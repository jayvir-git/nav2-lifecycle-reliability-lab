// Recorded experiment only: these controls never send commands to ROS.
const experiment = window.FAILURE;
const failed = experiment.runs[0];
const recovered = experiment.runs[1];
const fault = failed.result;
const killed = fault.events.find(e => e.event === 'controller_killed');
const aborted = fault.events.find(e => e.event === 'action_terminal');
const inactive = fault.state_samples.find(s => s.node === 'planner_server' && s.state === 'inactive');
const dt = t => (t - killed.seconds).toFixed(2);
const section = document.createElement('section');
section.className = 'evidence'; section.id = 'failure';
section.innerHTML = `<div class="eyebrow">05 / Controlled failure · recorded experiment</div>
<h2>We killed the controller.<br>The failure unfolded in stages.</h2>
<p><strong>Prediction:</strong> losing the controller's heartbeat should trigger coordinated deactivation. We did not assume when the action would end or whether shutdown would be graceful.</p>
<div class="lower"><div><div class="eyebrow">Healthy reference</div><div class="stat">SUCCEEDED</div><p>Two destinations reached within tolerance. Controller pause and resume worked. The original baseline shut down cleanly.</p></div><div><div class="eyebrow">Interrupted navigation</div><div class="stat">ABORTED</div><p id="fault-summary"></p></div></div>
<div class="layout"><div class="diagram"><div class="eyebrow">Recorded sequence / select an event</div><div id="fault-events" style="display:grid;gap:10px;margin:24px 0"></div><p class="small">Times are relative to our SIGKILL call, measured using the observer's monotonic clock. Lifecycle queries sample about once per second: these are first observations, not exact transition times.</p></div><div class="lesson" aria-live="polite"><div class="eyebrow" id="fault-time"></div><h2 id="fault-title"></h2><p id="fault-detail"></p><div id="fault-nodes" style="font:13px monospace;line-height:2"></div></div></div>
<div class="lower"><section><div class="eyebrow">Recovery that we actually tested</div><h2>Restart the whole stack.<br>Then navigate again.</h2><p id="recovery-result"></p><p>We shut down the failed run, launched a fresh stack, reset the simulated pose, and sent new goals. This demonstrates deliberate restart recovery. It does not demonstrate automatic respawn, resuming the interrupted goal, or replacing only the controller.</p></section><section><div class="eyebrow">Unresolved finding</div><h2>Cleanup needed a forced kill.</h2><p>The navigation lifecycle manager did not exit within the launch system's shutdown deadlines. The logs show escalation from SIGINT to SIGTERM to SIGKILL. A launcher exit code of zero did not reveal this child-process failure.</p><p>This observation warrants a separate investigation. It is not yet evidence of an upstream bug.</p></section></div>
<details><summary>What did we observe about motion?</summary><p>We collected simulated odometry. The final samples reported zero longitudinal velocity and unchanged position, but odometry then stopped arriving before the observation window ended. Those samples do not establish continuous standstill for the entire window.</p><p>The installed loopback simulator stops integrating stale velocity commands after one second and can stop publishing odometry while continuing transforms. Other nodes also affect commands. We have not isolated which mechanism caused the observed stop. Odometry uses its own frame; its x coordinate cannot be directly compared with the map-frame goal coordinates.</p></details>
<p class="small" id="fault-source"></p><p><a href="failure.json">Download full fault and recovery evidence</a></p>
<p>Repeat in the dedicated simulation: <code>.\\nav2-lab\\run.ps1 --failure-experiment</code></p>`;
document.querySelector('main').insertBefore(section, document.querySelector('main > section.evidence'));
const stages = [
  ['0.00 s', 'Controller process killed', 'Movement feedback crossed the trigger threshold. We sent SIGKILL only to the controller executable belonging to this experiment’s process group and user.', 'Controller: killed • peer states not yet sampled'],
  ['+'+dt(aborted.seconds)+' s', 'Navigation action aborted', 'The accepted navigation request returned ROS action status 6 (ABORTED). Request failure was observed before the later peer-node deactivation.', 'Goal: aborted • controller: unavailable'],
  ['+'+dt(inactive.seconds)+' s', 'Peer nodes observed inactive', 'The lifecycle manager logged a missing controller heartbeat and began deactivating related nodes. State queries found planner and navigator inactive. The separately managed map server remained active.', 'Planner: inactive • navigator: inactive • map: active'],
  ['+20 s', 'Observation ended', 'The controller was not restored during the observation window. During subsequent cleanup, the lifecycle manager required forced termination.', 'Observation complete • shutdown: forced escalation'],
  ['NEW RUN', 'Fresh navigation succeeded', 'After a deliberate full-stack restart and pose reset, both new goals succeeded. Controller pause and resume also passed.', 'New stack: active • goals: 2 / 2 succeeded']
];
function selectStage(index) {
  const s=stages[index];
  document.getElementById('fault-time').textContent=s[0];
  document.getElementById('fault-title').textContent=s[1];
  document.getElementById('fault-detail').textContent=s[2];
  document.getElementById('fault-nodes').textContent=s[3];
  [...document.getElementById('fault-events').children].forEach((b,i)=>b.setAttribute('aria-pressed',String(i===index)));
}
stages.forEach((s,i)=>{const b=document.createElement('button');b.textContent=s[0]+' / '+s[1];b.style.textAlign='left';b.onclick=()=>selectStage(i);document.getElementById('fault-events').appendChild(b)});
selectStage(0);
document.getElementById('fault-summary').textContent='Action failure observed '+dt(aborted.seconds)+' seconds after interruption. Planner first observed inactive '+dt(inactive.seconds)+' seconds after interruption.';
document.getElementById('recovery-result').textContent=recovered.result.goals.map((g,i)=>'Goal '+(i+1)+': '+g.seconds.toFixed(2)+' s, SUCCEEDED').join(' · ');
document.getElementById('fault-source').textContent='Source: fault '+failed.run+'; restart '+recovered.run+'. Recorded 2 October 2026 evening, America/New_York (3 October UTC). One selected run shown; a separate first trial is documented in the README.';
const closing = document.querySelector('main > section.evidence:last-child');
closing.querySelector('.eyebrow').textContent='06 / Why this is useful';
closing.querySelector('p:nth-of-type(2)').textContent='Next investigation: determine why the lifecycle manager needed forced termination. The controlled failure experiment above is implemented; the root cause of the shutdown behavior is not yet established.';
