// Conceptual animation backed by the separately recorded coordinated candidate.
const coordinated = window.COORDINATED;
const coordination = document.createElement('section');
coordination.className='evidence';coordination.id='coordination';
coordination.innerHTML=`<div class="eyebrow">11 / Revised candidate · initialization handoff</div>
<h2>Stop new work.<br>Wait before clearing shared state.</h2>
<p>The first prototype could interrupt a wait, but its startup callback did not handle that interruption. The revision also controls <em>who may touch the initialization state</em> while shutdown is underway.</p>
<div class="layout"><div class="diagram"><div class="eyebrow">Conceptual sequence / not a timing measurement</div>
<svg viewBox="0 0 620 410" role="img" aria-label="Set stop flag, wait for initialization, release mutex, join worker, then clear shared state.">
<path id="handoff-flow" class="flow" d="M310 65V95M310 155V185M310 245V275M310 335V355"/>
<rect class="node" id="handoff-0" x="10" y="5" width="600" height="60"/><text x="30" y="30" font-size="14">01 / SET STOP FLAG</text><text x="30" y="51" font-size="12">Let the waiting initializer know it must leave</text>
<rect class="node" id="handoff-1" x="10" y="95" width="600" height="60"/><text x="30" y="120" font-size="14">02 / WAIT FOR INITIALIZATION</text><text x="30" y="141" font-size="12">The mutex protects client and worker setup</text>
<rect class="node" id="handoff-2" x="10" y="185" width="600" height="60"/><text x="30" y="210" font-size="14">03 / RELEASE THE MUTEX</text><text x="30" y="231" font-size="12">A queued startup callback may need it to exit</text>
<rect class="node" id="handoff-3" x="10" y="275" width="600" height="60"/><text x="30" y="300" font-size="14">04 / JOIN THE WORKER</text><text x="30" y="321" font-size="12">Wait until it can no longer access the state</text>
<rect class="node" id="handoff-4" x="10" y="355" width="600" height="50"/><text x="30" y="386" font-size="14">05 / CLEAR TIMERS AND CONTAINERS</text></svg>
<div class="controls" id="handoff-steps"></div><button class="primary" id="handoff-play">Play the handoff</button>
</div><div class="lesson" aria-live="polite"><div class="eyebrow" id="handoff-label"></div><h2 id="handoff-title"></h2><p id="handoff-detail"></p><p class="small">A flag communicates intent. A mutex gives one thread access at a time. Joining waits for a thread to finish. Each has a different job.</p></div></div>
<div class="lower"><div><div class="eyebrow">Previously failing discovery path</div><div class="stat">${coordinated.discovery_passed} / ${coordinated.discovery_total}</div><p>Clean exits across five interruption delays, repeated three times. Baseline and first prototype still aborted in their control trials.</p></div><div><div class="eyebrow">Other service-wait checks</div><div class="stat">${coordinated.other_passed} / ${coordinated.other_total}</div><p>Healthy shutdown, a killed server, an interrupted transition, and a slow healthy transition all tested. No blanket transition deadline was added.</p></div></div>
<div class="eyebrow">Full navigation / new paired tests</div><h2>${coordinated.full_passed} / ${coordinated.full_total} candidate sequences passed.</h2><p>Each sequence includes controller failure, clean manager shutdown, fresh restart, two successful goals, and lifecycle pause/resume. The paired baseline runs retain their forced-shutdown outcome. Server response-delivery warnings in this batch: ${coordinated.response_warnings}.</p>
<p><strong>What this changes:</strong> the revised candidate now passes the discovery case that rejected the first prototype. It remains a 1.3.13 lab patch. Timing sweeps do not establish freedom from every data race.</p>
<p class="small">Not yet tested with ThreadSanitizer, custom multithreaded composition, other middleware, or as a patch to current main. The earlier intermittent response-delivery failure remains unexplained. No upstream issue or PR has been submitted.</p>
<p><a href="coordinated-validation.md">Design and reproduction</a> · <a href="coordinated-matrix.json">Every focused trial</a> · <a href="coordinated-reliability.json">Full-run evidence</a> · <a href="coordinated-prototype.patch">Review the revised patch</a></p>`;
document.querySelector('main').appendChild(coordination);
const handoffSteps=[
 ['Signal before waiting.','Shutdown sets the atomic stop flag first. If it took the mutex first, it could wait forever behind an initializer that is still waiting for a missing service.'],
 ['Let initialization unwind.','The initializer holds the mutex while constructing clients and creating the worker. It sees the stop flag, handles the shutdown interruption, and leaves its protected section. Shutdown can then acquire the mutex without clearing objects still in use.'],
 ['Do not hold the lock across join.','The queued startup callback also takes this mutex to inspect its timer and shutdown flag. Shutdown releases the mutex before joining, so that callback can acquire it, see the flag, and return.'],
 ['Wait for the worker to finish.','Existing service waits observe the same stop flag. Once the callback returns, the worker can exit. Joining confirms completion before shutdown clears the worker’s shared state.'],
 ['Clean up after the handoff.','With initialization out of its protected section and the worker stopped, shutdown destroys the bond timer and clears the node names, lifecycle clients, and bonds. Late initialization callbacks see the stop flag and return.']
];
let handoffIndex=0,handoffTimer=null;
function handoffStep(i){handoffIndex=i;document.getElementById('handoff-label').textContent=`STEP ${i+1} / 5`;document.getElementById('handoff-title').textContent=handoffSteps[i][0];document.getElementById('handoff-detail').textContent=handoffSteps[i][1];for(let n=0;n<5;n++){document.getElementById(`handoff-${n}`).classList.toggle('lit',n===i);document.getElementById('handoff-steps').children[n].setAttribute('aria-pressed',String(n===i));}}
function stopHandoff(){clearInterval(handoffTimer);handoffTimer=null;document.getElementById('handoff-play').textContent='Play the handoff';document.getElementById('handoff-flow').classList.remove('moving');}
handoffSteps.forEach((_,i)=>{const b=document.createElement('button');b.textContent=String(i+1).padStart(2,'0');b.setAttribute('aria-label',`Handoff step ${i+1}`);b.onclick=()=>{stopHandoff();handoffStep(i)};document.getElementById('handoff-steps').appendChild(b)});
document.getElementById('handoff-play').onclick=()=>{if(handoffTimer){stopHandoff();return}handoffStep(0);document.getElementById('handoff-play').textContent='Stop handoff';document.getElementById('handoff-flow').classList.add('moving');handoffTimer=setInterval(()=>{if(handoffIndex===4){stopHandoff();return}handoffStep(handoffIndex+1)},3000)};
handoffStep(0);
