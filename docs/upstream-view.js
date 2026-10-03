// Current review status, backed by pinned upstream and local execution evidence.
const reviewData=window.UPSTREAM;
const review=document.createElement('section');review.id='review';review.className='evidence';
review.innerHTML=`<div class="eyebrow">10 / Upstream review · the boundary of the fix</div>
<h2>The failure is real.<br>The prototype is incomplete.</h2>
<p>We checked newer source, ran the real processes, and tested another point in the lifecycle. A passing shutdown test does not establish that every startup and shutdown path works.</p>
<div class="lower"><div><div class="eyebrow">Current Jazzy / 645abd95</div><div class="stat">HANG REPRODUCED</div><p>Healthy control exited. After a managed server was killed and bond loss was detected, the manager remained alive beyond the five-second deadline. Both manager and utility libraries came from the pinned current branch.</p></div><div><div class="eyebrow">Current main / d7bf2ac0</div><h2 id="main-audit-status"></h2><p id="main-audit-detail"></p></div></div>
<div class="layout"><div class="diagram"><div class="eyebrow">Select where shutdown interrupts the lifecycle</div><div class="controls" id="boundary-choices"></div>
<svg viewBox="0 0 620 230" role="img" aria-label="Discovery, transition, and shutdown are separate stages. Discovery is still an uncovered failure path."><path class="flow" d="M190 92H230M390 92H430"/>
<rect class="node" id="boundary-0" x="10" y="52" width="180" height="80"/><text x="100" y="85" text-anchor="middle" font-size="14">FIND SERVICE</text><text x="100" y="111" text-anchor="middle" font-size="11">startup / discovery</text>
<rect class="node" id="boundary-1" x="230" y="52" width="160" height="80"/><text x="310" y="85" text-anchor="middle" font-size="14">WAIT FOR REPLY</text><text x="310" y="111" text-anchor="middle" font-size="11">transition request</text>
<rect class="node" id="boundary-2" x="430" y="52" width="180" height="80"/><text x="520" y="85" text-anchor="middle" font-size="14">STOP + JOIN</text><text x="520" y="111" text-anchor="middle" font-size="11">worker teardown</text>
<text x="310" y="185" text-anchor="middle" font-size="13">Cancellation must work at every entry point.</text></svg></div>
<div class="lesson" aria-live="polite"><div class="eyebrow" id="boundary-verdict"></div><h2 id="boundary-title"></h2><p id="boundary-detail"></p></div></div>
<div class="eyebrow">Repeated full experiments / all attempts counted</div><h2 id="repeat-title"></h2><p id="repeat-detail"></p>
<div style="border-left:5px solid var(--ink);padding:4px 24px;background:#e9dfca"><h2>Decision for the first prototype: keep it in the lab.</h2><p>A closely overlapping <a href="https://github.com/ros-navigation/navigation2/issues/6565">upstream report already exists</a>. Its closure cited contribution policy; that is not proof of a technical fix. We have not submitted another report or PR.</p><p>The next useful contribution requires a reproducible distinction, a reviewed implementation, and a human who can explain and maintain it. At that checkpoint, the discovery failure blocked the first prototype. The revised candidate is covered in the next section.</p></div>
<p class="small">Pinned source and run IDs: <a href="upstream-results.json">audit evidence</a> · <a href="upstream-main-backtrace.txt">main debugger trace</a> · <a href="reliability-summary.json">repeat summary</a> · <a href="upstream-review.md">review notes and commands</a> · <a href="cancellation-prototype.patch">experimental 1.3.13 patch</a></p>`;
document.querySelector('main').appendChild(review);
const boundaries=[
 ['FAIL / BOTH BUILDS','No server has appeared yet.','We interrupt the normal standalone manager while its first service is absent. Both baseline and candidate abort. The candidate throws an uncaught cancellation exception; the baseline throws from a sleep on an invalid ROS context. A fast crash is not a clean exit.'],
 ['PASS / CANDIDATE ONLY','The server cannot reply.','A healthy server is suspended during pause. The manager logs its deactivation request; then we interrupt it. The candidate exits cleanly, while the baseline is still alive after five seconds. Cleanup resumes the suspended server.'],
 ['PASS / TESTED DEAD-NODE PATH','The worker is allowed to finish.','After the server is killed and bond loss is detected, the candidate stop flag releases the blocked service wait so join can finish. The maintained Jazzy branch still hangs on this tested path. This result does not cover discovery-time initialization.']
];
function boundary(i){document.getElementById('boundary-verdict').textContent=boundaries[i][0];document.getElementById('boundary-title').textContent=boundaries[i][1];document.getElementById('boundary-detail').textContent=boundaries[i][2];for(let n=0;n<3;n++){document.getElementById(`boundary-${n}`).classList.toggle('lit',n===i);document.getElementById('boundary-choices').children[n].setAttribute('aria-pressed',String(n===i));}}
['Discovery','Transition','Worker join'].forEach((name,i)=>{const b=document.createElement('button');b.textContent=name;b.onclick=()=>boundary(i);document.getElementById('boundary-choices').appendChild(b)});boundary(0);
document.getElementById('main-audit-status').textContent=reviewData.main_status;
document.getElementById('main-audit-detail').textContent=reviewData.main_detail;
document.getElementById('repeat-title').textContent=reviewData.repeat_title;
document.getElementById('repeat-detail').textContent=reviewData.repeat_detail;
