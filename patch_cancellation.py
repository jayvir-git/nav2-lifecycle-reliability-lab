"""Apply a manager-local shutdown cancellation prototype to pinned Nav2 source."""
from pathlib import Path
import shutil
import sys
root=Path(sys.argv[1])/'nav2_lifecycle_manager'
header=root/'include/nav2_lifecycle_manager/lifecycle_manager.hpp'
source=root/'src/lifecycle_manager.cpp'
text=header.read_text()
if 'shutdown_requested_' not in text:
    text=text.replace('#include <memory>', '#include <memory>\n#include "nav2_lifecycle_manager/shutdown_lifecycle_client.hpp"')
    text=text.replace('protected:', 'protected:\n  std::shared_ptr<std::atomic_bool> shutdown_requested_ = std::make_shared<std::atomic_bool>(false);',1)
    text=text.replace('std::shared_ptr<nav2_util::LifecycleServiceClient>', 'std::shared_ptr<ShutdownLifecycleClient>')
    assert 'shutdown_lifecycle_client.hpp' in text
    header.write_text(text)
text=source.read_text()
if 'shutdown_requested_->store(true)' not in text:
    text=text.replace('using nav2_util::LifecycleServiceClient;', 'using LifecycleServiceClient = nav2_lifecycle_manager::ShutdownLifecycleClient;')
    text=text.replace('std::make_shared<LifecycleServiceClient>(node_name, shared_from_this())',
        'std::make_shared<LifecycleServiceClient>(node_name, shared_from_this(), shutdown_requested_)')
    text=text.replace('LifecycleManager::onRclPreshutdown()\n{',
        'LifecycleManager::onRclPreshutdown()\n{\n  shutdown_requested_->store(true);')
    assert text.count('shutdown_requested_->store(true)')==1
    source.write_text(text)
shutil.copyfile(Path(__file__).with_name('shutdown_lifecycle_client.hpp'),root/'include/nav2_lifecycle_manager/shutdown_lifecycle_client.hpp')
