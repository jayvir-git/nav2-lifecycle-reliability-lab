(async () => {
  const section=document.createElement('section'); section.className='evidence'; section.id='milestone';
  document.querySelector('main').appendChild(section);
  try {
    const [contextResponse,ciResponse]=await Promise.all([fetch('milestone-local-context.json'),fetch('milestone-ci.json')]);
    if(!contextResponse.ok||!ciResponse.ok) throw new Error('Evidence unavailable');
    const context=await contextResponse.json(),ci=await ciResponse.json();
    const passes=context.trials.filter(t=>t.passed).length;
    section.innerHTML=`<div class="eyebrow">13 / Review milestone · reproducible beyond this machine</div>
      <h2>A result another engineer<br>can try to break.</h2>
      <p><strong>The practical problem:</strong> a navigation server dies, but the manager remains stuck waiting for it. A supervisor trying to restart the stack then has to force-kill the manager. This lab gives another developer a way to reproduce that failure and test a candidate that exits cleanly in the recorded scenarios.</p>
      <p class="lede">The first port worked as a standalone process, then crashed when embedded with its own ROS context. A new test exposed the assumption. We fixed it and took the experiment to independent Linux runners.</p>
      <p>A <strong>ROS context</strong> tracks one ROS runtime's startup and shutdown inside a program. An application can create its own instead of using the global default. Checking the wrong context is like checking whether a different machine is switched on.</p>
      <div class="layout"><div class="diagram"><div class="eyebrow">CONCEPTUAL OWNERSHIP / NOT A TRACE</div>
      <svg viewBox="0 0 520 330" role="img" aria-label="A manager and its service client must use their caller's ROS context, rather than an uninitialized global context.">
        <rect class="node" x="18" y="25" width="484" height="95"/><text x="38" y="57" font-size="15">GLOBAL CONTEXT</text><text x="38" y="85" font-size="12">Not initialized by this embedding application</text>
        <rect class="node" id="context-owned" x="18" y="175" width="484" height="135"/><text x="38" y="204" font-size="15">CALLER'S CONTEXT</text><text x="38" y="230" font-size="12">Initialized · owns the node's lifetime</text>
        <rect class="node" x="38" y="252" width="200" height="36"/><text x="52" y="275" font-size="12">Lifecycle manager</text>
        <rect class="node" x="264" y="252" width="210" height="36"/><text x="277" y="275" font-size="12">Client + worker executor</text>
        <path id="context-arrow" class="flow" d="M369 252 V120"/>
      </svg><div class="controls" id="milestone-steps"></div><button class="primary" id="milestone-play">Play the reasoning</button></div>
      <div class="lesson" aria-live="polite"><div class="eyebrow" id="milestone-step"></div><h2 id="milestone-title"></h2><p id="milestone-explain"></p><p class="small">The test uses real ROS and manager APIs. It does not inject private-state hooks or simulate a passing result.</p></div></div>
      <div class="lower"><div><div class="eyebrow">LOCAL CONTEXT REGRESSIONS</div><div class="stat">${passes} / ${context.trials.length}</div><p>Before executor spin, missing-service discovery, and initialization with an empty node list. Repeated with timing variation.</p></div><div><div class="eyebrow">INDEPENDENT LINUX VALIDATION</div><div id="independent-results"></div><p class="small">Each successful job must pass its failing-control checks as well as the candidate tests. Container and dependency details are retained in CI logs and artifacts.</p></div></div>
      <p><strong>The useful deliverable:</strong> a pinned failure and a candidate that another developer can build, test, and reject. This is evidence for review, not a production certification or proof of demand.</p>
      <details class="lesson"><summary>Second finding: the replacement had different message-delivery settings.</summary><p>A direct observation in our Fast DDS environment showed that middleware defaults gave service responses best-effort delivery with depth 1. Upstream explicitly requests reliable service delivery with depth 10. The final candidate now preserves that profile.</p><p>That is a measured compatibility difference. We did not capture a lost packet or prove it caused each earlier timeout. <a href="qos-observation.md">Inspect the measurement and source.</a></p></details>
      <p><strong>Unresolved:</strong> an earlier Rolling trial timed out during startup. Later clean batches do not explain or erase it. <a href="rolling-first-matrix.json">That failed trial is preserved.</a></p>
      <p>Still outside this milestone: exhaustive concurrency checking, full navigation for this main-source port, and upstream design acceptance. No maintainer message or PR has been sent.</p>
      <p><a href="reviewable-milestone.md">Review the milestone</a> · <a href="main-context.patch">Current patch</a> · <a href="milestone-local-context.json">Final local context trials</a> · <a href="milestone-local-main.json">Final local process trials</a> · <a href="milestone-ci.json">Independent evidence index</a></p>`;
    const result=section.querySelector('#independent-results');
    for(const job of ci.jobs){const p=document.createElement('p');const a=document.createElement('a');a.href=job.url;a.textContent=job.name+' — '+job.status;p.appendChild(a);result.appendChild(p);}
    const lessons=[['Find the hidden assumption.','The caller initialized a separate context. The old client checked the uninitialized global one, threw during initialization, and the process aborted. Passing standalone tests had missed this.'],['Keep ownership consistent.','The client now checks the node’s own context. Both its executor and the manager’s worker executor use that context too. The previously failing test then exits cleanly.'],['Make the result challengeable.','CI starts in a fresh ROS container, downloads checksummed source, builds the needed components, and runs both the original failure control and the candidate. Logs preserve what actually happened.']];
    let index=0,timer=null;const controls=section.querySelector('#milestone-steps');
    function stop(){clearInterval(timer);timer=null;section.querySelector('#milestone-play').textContent='Play the reasoning';section.querySelector('#context-arrow').classList.remove('moving');}
    function render(i){index=i;section.querySelector('#milestone-step').textContent=`STEP ${i+1} / 3`;section.querySelector('#milestone-title').textContent=lessons[i][0];section.querySelector('#milestone-explain').textContent=lessons[i][1];[...controls.children].forEach((b,j)=>b.setAttribute('aria-pressed',String(i===j)));section.querySelector('#context-owned').classList.toggle('lit',i>0);section.querySelector('#context-arrow').setAttribute('d',i===0?'M369 252 V120':'M264 270 H238');}
    lessons.forEach((_,i)=>{const b=document.createElement('button');b.textContent=['Break','Fix','Reproduce'][i];b.onclick=()=>{stop();render(i)};controls.appendChild(b)});
    section.querySelector('#milestone-play').onclick=()=>{if(timer){stop();return}render(0);section.querySelector('#context-arrow').classList.add('moving');section.querySelector('#milestone-play').textContent='Stop reasoning';timer=setInterval(()=>{if(index===2){stop();return}render(index+1)},3500)};render(0);
  }catch(error){section.textContent='Milestone evidence could not be loaded: '+error.message;}
})();
