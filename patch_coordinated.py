"""Layer initialization/shutdown coordination onto the isolated 1.3.13 prototype."""
from pathlib import Path
import subprocess
import sys

subprocess.run([sys.executable,str(Path(__file__).with_name('patch_cancellation.py')),sys.argv[1]],check=True)
root=Path(sys.argv[1])/'nav2_lifecycle_manager'
upstream_main='--upstream-main' in sys.argv[2:]
header=root/'include/nav2_lifecycle_manager/lifecycle_manager.hpp'
source=root/'src/lifecycle_manager.cpp'
h=header.read_text()
if 'initialization_mutex_' not in h:
    h=h.replace('#include <memory>','#include <memory>\n#include <mutex>',1)
    h=h.replace('protected:', 'protected:\n  std::mutex initialization_mutex_;',1)
    header.write_text(h)
s=source.read_text()
if 'initialization_mutex_' not in s:
    old='''    [this]() -> void {
      init_timer_->cancel();
      createLifecycleServiceClients();'''
    new='''    [this]() -> void {
      // Shutdown sets its flag before taking this lock, so discovery can unwind.
      std::lock_guard<std::mutex> initialization_lock(initialization_mutex_);
      if (shutdown_requested_->load()) {
        return;
      }
      init_timer_->cancel();
      try {
        createLifecycleServiceClients();
      } catch (const std::runtime_error &) {
        if (shutdown_requested_->load()) {
          return;
        }
        throw;
      }
      if (shutdown_requested_->load()) {
        return;
      }'''
    if upstream_main:
        old=old.replace('      createLifecycleServiceClients();', '      createLifecyclePublishers();\n      createLifecycleServiceClients();\n      createLifecycleServiceServers();')
        new=new.replace('        createLifecycleServiceClients();', '        createLifecyclePublishers();\n        createLifecycleServiceClients();\n        createLifecycleServiceServers();')
        new=new.replace('const std::runtime_error &', 'const ShutdownCancelled &')
    assert s.count(old)==1
    s=s.replace(old,new,1)
    old='''          [this]() -> void {
            init_timer_->cancel();
            startup();'''
    new='''          [this]() -> void {
            {
              std::lock_guard<std::mutex> startup_lock(initialization_mutex_);
              if (shutdown_requested_->load()) {
                return;
              }
              init_timer_->cancel();
            }
            startup();'''
    assert s.count(old)==1
    s=s.replace(old,new,1)
    start=s.index('LifecycleManager::onRclPreshutdown()')
    end=s.index('\nvoid\nLifecycleManager::registerRclPreshutdownCallback()',start)
    s=s[:start]+'''LifecycleManager::onRclPreshutdown()
{
  shutdown_requested_->store(true);
  RCLCPP_INFO(get_logger(), "Coordinated lifecycle manager preshutdown");
  {
    // Wait for client initialization to stop before touching its containers.
    std::lock_guard<std::mutex> shutdown_lock(initialization_mutex_);
    if (init_timer_) {
      init_timer_->cancel();
    }
  }
  // Never hold initialization_mutex_ across join: a queued startup callback
  // may need that lock to observe shutdown and return.
  service_thread_.reset();
  // The worker can no longer create/reset the bond timer or access these maps.
  destroyBondTimer();
  node_names_.clear();
  node_map_.clear();
  bond_map_.clear();
}
''' +s[end:]
    source.write_text(s)
