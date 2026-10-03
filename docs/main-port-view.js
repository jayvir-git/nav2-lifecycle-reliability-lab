// Display actual probe outcomes; diagram is conceptual, not a measured timeline.
(async () => {
  const section=document.createElement('section'); section.className='evidence'; section.id='main-port';
  document.querySelector('main').appendChild(section);
  try {
    const response=await fetch('main-matrix.json'); if(!response.ok) throw new Error('Evidence unavailable');
    const report=await response.json();
    const candidates=report.trials.filter(t=>t.result.variant==='main-coordinated');
    const discoveries=candidates.filter(t=>t.result.mode==='discovery');
    const waits=candidates.filter(t=>t.result.mode!=='discovery');
    const passed=items=>items.filter(t=>t.expectation_met).length;
    section.innerHTML=`<div class="eyebrow">12 / Pinned main · same failure, new source</div>
      <h2>The shutdown fix now has<br>evidence on newer source.</h2>
      <p>We ported the experiment to main commit <code>d7bf2ac0</code>, preserved its configurable service-timeout arguments, and separated cancellation from unrelated runtime errors. Select a build to compare the killed-server outcome.</p>
      <div class="controls"><button id="main-stock" aria-pressed="true">Unmodified main</button> <button id="main-patched" aria-pressed="false">Patched main</button></div>
      <div class="lesson" aria-live="polite"><div class="eyebrow">CONCEPTUAL CONTROL FLOW</div><h3 id="main-flow"></h3><p id="main-outcome"></p></div>
      <div class="lower"><div class="card"><div class="eyebrow">DISCOVERY INTERRUPTIONS</div><h2>${passed(discoveries)} / ${discoveries.length}</h2><p>Three delay settings, each repeated twice. All attempted trials are included.</p></div>
      <div class="card"><div class="eyebrow">OTHER CANDIDATE CHECKS</div><h2>${passed(waits)} / ${waits.length}</h2><p>Healthy shutdown, killed server, interrupted transition, and delayed healthy transition.</p></div></div>
      <p><strong>What this establishes:</strong> the observed improvement extends beyond the old 1.3.13 source. The unmodified-main healthy control still exits cleanly; its killed-server control still hangs.</p>
      <p><strong>Boundary:</strong> main-source manager on Jazzy / WSL, not native Rolling. This port has not run the full navigation experiment. No ThreadSanitizer result, exhaustive concurrency proof, or upstream submission is claimed.</p>
      <p><a href="main-port-review.md">Concurrency review and reproduction</a> · <a href="main-matrix.json">Every trial and log</a> · <a href="main-coordinated.patch">Exact source patch</a></p>`;
    function select(patched) {
      section.querySelector('#main-stock').setAttribute('aria-pressed',String(!patched));
      section.querySelector('#main-patched').setAttribute('aria-pressed',String(patched));
      section.querySelector('#main-flow').textContent=patched?'Signal stop → worker returns → join completes':'Join worker → worker waits for dead server → still waiting';
      const trial=report.trials.find(t=>t.result.variant===(patched?'main-coordinated':'upstream-main')&&t.result.mode==='dead');
      section.querySelector('#main-outcome').textContent=patched?`Recorded clean exit: ${trial.result.shutdown_seconds} seconds after SIGINT. One probe, not a timing guarantee.`:'Still alive after the five-second deadline; the harness forced termination. This is the expected failing control.';
    }
    section.querySelector('#main-stock').onclick=()=>select(false);
    section.querySelector('#main-patched').onclick=()=>select(true);select(false);
  } catch(error) {section.textContent='Main-port evidence could not be loaded: '+error.message;}
})();
