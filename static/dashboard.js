const q=id=>document.getElementById(id), esc=v=>String(v??"—").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('\"',"&quot;");
const I18N={
  en:{
    subtitle:'Internal hosts, network devices & HTTPS · availability and response stability',
    servers_online:'TARGETS ONLINE', outages_24h:'OUTAGES · LAST 24 HOURS', poll_cycle:'POLL CYCLE',
    last_change:'LAST STATE CHANGE', last_outage:'LAST OUTAGE', predicted:'PREDICTED STABILITY · NEXT 15 MIN',
    live_targets:'MONITORED TARGETS', server_stability:'Infrastructure stability',
    healthy:'Healthy', unreachable:'Unavailable / service down',
    event_log:'EVENT LOG', history:'Outage & recovery history', reset:'Reset history & totals',
    all_targets:'All targets', observed:'Observed', target:'Target', event:'Event', detail:'Detail',
    waiting:'Waiting for first check…',
    footer:'Open “Graphs” on any target for response-time and availability history. Host targets use debounced ICMP/TCP stability (3 of 5 by default); HTTP/HTTPS targets use a real GET with phase timing. A single failed check counts as packet loss, not an outage.',
    graph_history:'HISTORY', range_1h:'1 hour', range_6h:'6 hours', range_24h:'24 hours',
    range_7d:'7 days', range_30d:'30 days', response_time:'RESPONSE TIME',
    latency_web:'Latency / web response', availability:'AVAILABILITY',
    successful_checks:'Successful checks per interval', state_changes:'STATE CHANGES',
    outages_range:'Outages & recoveries in selected range', light:'Light', dark:'Dark',
    no_state:'No state change recorded', no_outage:'No outage recorded',
    building_model:'Building short-term model', ongoing:'ONGOING', checking:'CHECKING',
    offline:'OFFLINE', degraded:'DEGRADED', stability_ux:'STABILITY / USER EXPERIENCE',
    predicted_next:'PREDICTED STABILITY · NEXT 15 MIN', risk:'Risk', confidence:'confidence',
    no_data:'NO DATA', waiting_history:'Waiting for history', building_trend:'Building recent trend',
    uptime:'AVAILABILITY · 24H', failure:'LOSS · 24H', avg_response:'AVG RESPONSE · 24H',
    jitter:'JITTER · 24H', loss_1m:'LOSS · 1 MIN', loss_5m:'LOSS · 5 MIN', loss_15m:'LOSS · 15 MIN',
    baseline:'BASELINE', adaptive:'ADAPTIVE BASELINE', current_get:'Current total GET',
    current_ping:'Current ping', check:'Check', outage_rule:'Outage rule', failed:'failed',
    threshold:'threshold', consecutive:'Consecutive failures', total_failures:'Total failures / checks',
    last_online:'Last reachable', tls_cert:'TLS certificate', days:'days',
    transient:'Transient failed check — counted as packet loss, not an outage',
    recent_failed:'recent checks failed', tls_expires:'TLS certificate expires in',
    alert_active:'EMAIL ALERT ACTIVE · since', degradation_timer:'DEGRADATION TIMER · since',
    recovery_timer:'RECOVERY CONFIRMATION RUNNING', graphs:'Graphs', target_word:'target',
    targets_word:'targets', online:'online', ungrouped:'Ungrouped', at_risk:'at risk',
    high_risk:'high risk', no_state_changes:'No state changes recorded yet.',
    reset_confirm:'Reset stored samples, events and totals?', no_samples:'No samples in this period.',
    no_response_samples:'No response-time samples in this period.', loading_history:'Loading history…',
    sec_buckets:'s intervals', min_buckets:'min intervals', hr_buckets:'h intervals',
    range_availability:'AVAILABILITY IN RANGE', avg_total_response:'AVG TOTAL RESPONSE',
    p95p99:'P95 / P99 RESPONSE', samples_resolution:'SAMPLES / RESOLUTION',
    avg_dns:'AVG DNS', avg_tcp:'AVG TCP CONNECT', avg_tls:'AVG TLS',
    avg_server:'AVG SERVER RESPONSE', no_outages_range:'No outages or recoveries in this period.',
    graph_error:'Could not load graph data', verified:'verified', no_verify:'verification off',
    n_a:'N/A', live:'LIVE', language:'Language', close:'Close',
    started:'started', recovered:'recovered', duration:'duration',
    grade_EXCELLENT:'EXCELLENT', grade_GOOD:'GOOD', grade_FAIR:'FAIR',
    grade_POOR:'POOR', grade_CRITICAL:'CRITICAL', grade_STABLE:'STABLE',
    grade_WATCH:'WATCH', grade_HIGH_RISK:'HIGH RISK', grade_LOW_RISK:'LOW RISK',
    category_RECOVERED:'RECOVERED', category_OFFLINE:'OFFLINE', category_ONLINE:'ONLINE',
    category_DEGRADED:'DEGRADED', category_ALERT:'ALERT', category_ALERT_RECOVERED:'ALERT RECOVERED', settings:'Settings', configuration:'CONFIGURATION', runtime_settings:'Runtime settings', settings_help:'Saved directly to config.json. Existing values are preserved; missing defaults are added automatically.', save_apply:'Save & apply', use_defaults:'Use defaults', saved:'Saved and applied', saving:'Saving…', save_failed:'Could not save settings', restart_monitor:'Restart monitor', restart_confirm:'Restart the monitor now? Monitoring will be unavailable briefly.', restarting:'Restarting monitor…', restart_failed:'Restart failed', back_online:'Monitor is back online', target_manager:'Targets & Groups', runtime_tab:'Runtime', manager_help:'Edit groups and monitored IP/WEB targets. Saving target changes requires a restart.', add_group:'+ Group', add_target:'+ Target', save_targets_restart:'Save targets & restart', index:'Index', name:'Name', type:'Type', address:'IP / URL', port:'Port', group:'Group', options:'Options', host_type:'IP / TCP', web_type:'WEB', verify_ssl_short:'Verify TLS', expected_status_short:'Expected status', delete_word:'Delete', move_up:'Up', move_down:'Down', group_name:'Group name', rename_group:'Rename group', delete_group:'Delete group', targets_saved:'Targets saved. Restarting…', targets_save_failed:'Could not save targets', confirm_delete_target:'Delete this target?', confirm_delete_group:'Delete this group? Its targets will become ungrouped.', category_ALERT_ESCALATED:'ALERT ESCALATED', category_FLAPPING:'FLAPPING', maintenance:'MAINTENANCE', alert_suppressed:'ALERTS SUPPRESSED', dependency_down:'DEPENDENCY UNAVAILABLE', flapping:'FLAPPING', content_check:'CONTENT CHECK', escalated:'ESCALATED', category_PATH_DEGRADED:'PATH DEGRADED', category_PATH_RECOVERED:'PATH RECOVERED', category_ALERT_REMINDER:'ALERT REMINDER', category_ALERT_TEST:'TEST E-MAIL', search_targets:'Search targets…', problems_only:'Problems only', showing:'showing', no_match:'No targets match the current filter.', monitor_unreachable:'NO CONNECTION', collector_stalled:'STALLED', test_email:'Send test e-mail', test_email_sent:'Test e-mail sent', test_email_failed:'Test e-mail failed', sending:'Sending…', export_csv:'Download raw samples (CSV)', section_core:'Polling & history', section_detection:'Outage detection', section_startup:'Startup reconciliation', section_baseline:'Baseline & anomalies', section_path:'Active path health', section_alerts:'E-mail alerts'
  },
  cs:{
    subtitle:'Interní zařízení, síť a HTTPS · dostupnost a stabilita odezvy',
    servers_online:'ZAŘÍZENÍ ONLINE', outages_24h:'VÝPADKY · POSLEDNÍCH 24 H', poll_cycle:'INTERVAL KONTROLY',
    last_change:'POSLEDNÍ ZMĚNA STAVU', last_outage:'POSLEDNÍ VÝPADEK', predicted:'PREDIKCE STABILITY · DALŠÍCH 15 MIN',
    live_targets:'MONITOROVANÁ ZAŘÍZENÍ', server_stability:'Stabilita infrastruktury',
    healthy:'V pořádku', unreachable:'Nedostupné / služba neodpovídá',
    event_log:'PROTOKOL UDÁLOSTÍ', history:'Historie výpadků a obnovení provozu',
    reset:'Vymazat historii a součty', all_targets:'Všechna zařízení',
    observed:'Čas', target:'Zařízení', event:'Událost', detail:'Podrobnosti',
    waiting:'Čekám na první kontrolu…',
    footer:'Otevřete „Grafy“ u libovolného zařízení pro historii odezvy a dostupnosti. Hosty používají filtrované ICMP/TCP vyhodnocení (výchozí pravidlo 3 z 5); HTTP/HTTPS cíle používají skutečný GET s měřením jednotlivých fází. Jediná neúspěšná kontrola se počítá jako ztráta paketu, nikoli jako výpadek.',
    graph_history:'HISTORIE', range_1h:'1 hodina', range_6h:'6 hodin', range_24h:'24 hodin',
    range_7d:'7 dní', range_30d:'30 dní', response_time:'DOBA ODEZVY',
    latency_web:'Latence / odezva webu', availability:'DOSTUPNOST',
    successful_checks:'Úspěšné kontroly v intervalu', state_changes:'ZMĚNY STAVU',
    outages_range:'Výpadky a obnovení ve zvoleném období', light:'Světlý', dark:'Tmavý',
    no_state:'Změna stavu zatím nebyla zaznamenána', no_outage:'Výpadek zatím nebyl zaznamenán',
    building_model:'Vytvářím krátkodobou predikci', ongoing:'TRVÁ', checking:'OVĚŘOVÁNÍ',
    offline:'NEDOSTUPNÉ', degraded:'ZHORŠENÉ', stability_ux:'STABILITA / UŽIVATELSKÝ DOPAD',
    predicted_next:'PREDIKCE STABILITY · DALŠÍCH 15 MIN', risk:'Riziko', confidence:'jistota',
    no_data:'BEZ DAT', waiting_history:'Čekám na dostatek dat', building_trend:'Vyhodnocuji krátkodobý trend',
    uptime:'DOSTUPNOST · 24 H', failure:'ZTRÁTA · 24 H', avg_response:'PRŮM. ODEZVA · 24 H',
    jitter:'JITTER · 24 H', loss_1m:'ZTRÁTA · 1 MIN', loss_5m:'ZTRÁTA · 5 MIN', loss_15m:'ZTRÁTA · 15 MIN',
    baseline:'BĚŽNÁ HODNOTA', adaptive:'ADAPTIVNÍ REFERENČNÍ HODNOTA',
    current_get:'Aktuální celkový GET', current_ping:'Aktuální ping', check:'Typ kontroly',
    outage_rule:'Pravidlo výpadku', failed:'selhání', threshold:'limit',
    consecutive:'Selhání v řadě', total_failures:'Celkem selhání / kontrol',
    last_online:'Naposledy dostupné', tls_cert:'TLS certifikát', days:'dní',
    transient:'Jednorázové selhání — započítáno jako ztráta paketu, nikoli jako výpadek',
    recent_failed:'posledních kontrol selhalo', tls_expires:'TLS certifikát vyprší za',
    alert_active:'E-MAILOVÝ ALARM AKTIVNÍ · od', degradation_timer:'ČASOVAČ ZHORŠENÍ · od',
    recovery_timer:'PROBÍHÁ POTVRZENÍ OBNOVENÍ', graphs:'Grafy',
    target_word:'zařízení', targets_word:'zařízení', online:'online',
    ungrouped:'Nezařazené', at_risk:'ohrožených', high_risk:'vysoké riziko',
    no_state_changes:'Zatím nebyly zaznamenány žádné změny stavu.',
    reset_confirm:'Opravdu vymazat uložené vzorky, události a součty?',
    no_samples:'V tomto období nejsou žádná data.',
    no_response_samples:'V tomto období nejsou žádná data o době odezvy.',
    loading_history:'Načítám historii…', sec_buckets:'s interval', min_buckets:'min interval', hr_buckets:'h interval',
    range_availability:'DOSTUPNOST V OBDOBÍ', avg_total_response:'PRŮM. CELKOVÁ ODEZVA',
    p95p99:'ODEZVA P95 / P99', samples_resolution:'VZORKY / ROZLIŠENÍ',
    avg_dns:'PRŮM. DNS', avg_tcp:'PRŮM. TCP SPOJENÍ', avg_tls:'PRŮM. TLS',
    avg_server:'PRŮM. ODEZVA SERVERU',
    no_outages_range:'V tomto období nebyl zaznamenán žádný výpadek ani obnovení.',
    graph_error:'Data grafu se nepodařilo načíst', verified:'ověření zapnuto',
    no_verify:'ověření vypnuto', n_a:'N/A', live:'ŽIVĚ', language:'Jazyk', close:'Zavřít',
    started:'začátek', recovered:'obnoveno', duration:'doba trvání',
    grade_EXCELLENT:'VÝBORNÁ', grade_GOOD:'DOBRÁ', grade_FAIR:'USPOKOJIVÁ',
    grade_POOR:'ŠPATNÁ', grade_CRITICAL:'KRITICKÁ', grade_STABLE:'STABILNÍ',
    grade_WATCH:'SLEDOVAT', grade_HIGH_RISK:'VYSOKÉ RIZIKO', grade_LOW_RISK:'NÍZKÉ RIZIKO',
    category_RECOVERED:'OBNOVENO', category_OFFLINE:'VÝPADEK', category_ONLINE:'ONLINE',
    category_DEGRADED:'ZHORŠENO', category_ALERT:'ALARM', category_ALERT_RECOVERED:'ALARM UKONČEN', settings:'Nastavení', configuration:'KONFIGURACE', runtime_settings:'Nastavení za běhu', settings_help:'Ukládá se přímo do config.json. Vaše existující hodnoty zůstávají zachovány; chybějící výchozí hodnoty se doplní automaticky.', save_apply:'Uložit a použít', use_defaults:'Výchozí hodnoty', saved:'Uloženo a použito', saving:'Ukládám…', save_failed:'Nastavení se nepodařilo uložit', restart_monitor:'Restartovat monitor', restart_confirm:'Opravdu nyní restartovat monitor? Monitoring bude krátce nedostupný.', restarting:'Restartuji monitor…', restart_failed:'Restart se nepodařil', back_online:'Monitor je znovu online', target_manager:'Zařízení a skupiny', runtime_tab:'Provoz', manager_help:'Upravujte skupiny a monitorované IP/WEB cíle. Uložení změn cílů vyžaduje restart.', add_group:'+ Skupina', add_target:'+ Zařízení', save_targets_restart:'Uložit cíle a restartovat', index:'Pořadí', name:'Název', type:'Typ', address:'IP / URL', port:'Port', group:'Skupina', options:'Volby', host_type:'IP / TCP', web_type:'WEB', verify_ssl_short:'Ověřit TLS', expected_status_short:'Očekávaný stav', delete_word:'Smazat', move_up:'Nahoru', move_down:'Dolů', group_name:'Název skupiny', rename_group:'Přejmenovat skupinu', delete_group:'Smazat skupinu', targets_saved:'Cíle uloženy. Restartuji…', targets_save_failed:'Cíle se nepodařilo uložit', confirm_delete_target:'Smazat toto zařízení?', confirm_delete_group:'Smazat tuto skupinu? Její zařízení budou nezařazená.', category_ALERT_ESCALATED:'ALARM ESKALOVÁN', category_FLAPPING:'KOLÍSÁNÍ STAVU', maintenance:'ÚDRŽBA', alert_suppressed:'ALARMY POTLAČENY', dependency_down:'NEDOSTUPNÁ ZÁVISLOST', flapping:'KOLÍSÁNÍ STAVU', content_check:'KONTROLA OBSAHU', escalated:'ESKALOVÁNO', category_PATH_DEGRADED:'ZHORŠENÁ CESTA', category_PATH_RECOVERED:'CESTA OBNOVENA', category_ALERT_REMINDER:'PŘIPOMENUTÍ ALARMU', category_ALERT_TEST:'TESTOVACÍ E-MAIL', search_targets:'Hledat zařízení…', problems_only:'Jen problémy', showing:'zobrazeno', no_match:'Filtru neodpovídá žádné zařízení.', monitor_unreachable:'BEZ SPOJENÍ', collector_stalled:'ZASTAVENO', test_email:'Odeslat testovací e-mail', test_email_sent:'Testovací e-mail odeslán', test_email_failed:'Testovací e-mail se nepodařilo odeslat', sending:'Odesílám…', export_csv:'Stáhnout surová data (CSV)', section_core:'Kontroly a historie', section_detection:'Detekce výpadku', section_startup:'Ověření po startu', section_baseline:'Referenční hodnota a anomálie', section_path:'Aktivní kvalita cesty', section_alerts:'E-mailové alarmy'
  }
}
let LANG=localStorage.getItem('ip-monitor-lang')||null;
const tr=k=>(I18N[LANG]||I18N.en)[k]??I18N.en[k]??k;
const num=v=>{const n=Number(v);return Number.isFinite(n)?String(n):'0';};

const loc=()=>LANG==='cs'?'cs-CZ':'en-GB';
function targetCount(n){
  n=Number(n)||0;
  if(LANG!=='cs') return `${n} ${n===1?'target':'targets'}`;
  return `${n} ${n===1?'zařízení':'zařízení'}`;
}
function durationText(seconds){
  if(seconds==null || !Number.isFinite(Number(seconds))) return '—';
  let s=Math.max(0,Math.round(Number(seconds)));
  const d=Math.floor(s/86400); s%=86400;
  const h=Math.floor(s/3600); s%=3600;
  const m=Math.floor(s/60); s%=60;
  const parts=[];
  if(d) parts.push(LANG==='cs'?`${d} d`:`${d}d`);
  if(h) parts.push(LANG==='cs'?`${h} h`:`${h}h`);
  if(m) parts.push(LANG==='cs'?`${m} min`:`${m}m`);
  if(!parts.length || (d===0&&h===0&&m<2)) parts.push(LANG==='cs'?`${s} s`:`${s}s`);
  return parts.slice(0,2).join(' ');
}
function localCheck(v){
  const x=String(v||'').toLowerCase();
  if(!x)return '—';
  if(x==='http')return 'HTTP GET';
  if(x==='host')return LANG==='cs'?'ICMP / TCP':'ICMP / TCP';
  return v;
}

function localGrade(v){if(!v)return tr('no_data');const k='grade_'+String(v).toUpperCase().replaceAll(' ','_').replaceAll('-','_');return tr(k)!==k?tr(k):v}
function localCategory(v){if(!v)return '—';const k='category_'+String(v).toUpperCase();return tr(k)!==k?tr(k):v}
function localAnomaly(v){if(!v)return tr('no_data');if(LANG!=='cs')return v;return ({'NO DATA':'BEZ DAT','LEARNING':'UČENÍ','NORMAL':'NORMÁLNÍ','ELEVATED':'ZVÝŠENÁ','HIGH':'VYSOKÁ','SEVERE':'KRITICKÁ'})[String(v).toUpperCase()]||v}
function localDetail(v){
  if(!v)return '';
  let z=String(v);
  if(LANG!=='cs')return z;
  z=z.replace(/^Target reachable again after stability confirmation$/i,'Zařízení je po potvrzení stability znovu dostupné');
  z=z.replace(/endpoint stable\/reachable again/gi,'koncový bod je znovu stabilní a dostupný');
  z=z.replace(/^Confirmed outage:/i,'Potvrzený výpadek:');
  z=z.replace(/(\d+)\/(\d+) recent checks failed/gi,'$1/$2 posledních kontrol selhalo');
  z=z.replace(/ConnectionRefusedError[^:]*:\s*/gi,'Připojení odmítnuto: ');
  z=z.replace(/Connection refused/gi,'Připojení odmítnuto');
  z=z.replace(/timed out/gi,'vypršel časový limit');
  z=z.replace(/Name or service not known/gi,'název nebo služba nebyla nalezena');
  z=z.replace(/Temporary failure in name resolution/gi,'dočasná chyba překladu názvu');
  z=z.replace(/^Recovered after\s+(\d+)\s+seconds?/i,(_,n)=>`Obnoveno po ${durationText(Number(n))}`);
  z=z.replace(/certificate verify failed/gi,'ověření certifikátu selhalo');
  return z;
}
function localSummary(v){
  if(!v)return v;
  let z=String(v);
  if(LANG!=='cs')return z;
  const pairs=[
    ['currently offline','aktuálně nedostupné'],
    ['Stable response and availability','Stabilní odezva a dostupnost'],
    ['No short-term instability signals','Bez známek krátkodobé nestability'],
    ['packet loss is rising','ztráta paketů roste'],
    ['packet loss','ztráta paketů'],
    ['latency anomaly','anomálie latence'],
    ['average response','průměrná odezva'],
    ['high latency anomaly','výrazná anomálie latence'],
    ['elevated latency anomaly','zvýšená anomálie latence'],
    ['severe latency anomaly','kritická anomálie latence'],
    ['recent failures','nedávná selhání'],
    ['insufficient history','nedostatek historie'],
    ['healthy baseline','stabilní referenční hodnota']
  ];
  for(const [a,b] of pairs)z=z.replaceAll(a,b);
  return z;
}
function applyLanguage(){
  document.documentElement.lang=LANG==='cs'?'cs':'en';
  document.title=LANG==='cs'?'Monitor stability IP':'Internal IP Stability Monitor';
  q('subtitle').textContent=tr('subtitle');
  const ids={
    'lbl-servers-online':'servers_online','lbl-outages-24h':'outages_24h','lbl-poll-cycle':'poll_cycle',
    'lbl-last-change':'last_change','lbl-last-outage':'last_outage','lbl-predicted':'predicted',
    'lbl-live-targets':'live_targets','lbl-server-stability':'server_stability','lbl-healthy':'healthy',
    'lbl-unreachable':'unreachable','lbl-event-log':'event_log','lbl-history':'history',
    'reset-monitor':'reset','all-targets-option':'all_targets','th-observed':'observed','th-target':'target',
    'th-event':'event','th-detail':'detail','footer-help':'footer','lbl-graph-history':'graph_history',
    'range-1h':'range_1h','range-6h':'range_6h','range-24h':'range_24h','range-7d':'range_7d',
    'range-30d':'range_30d','lbl-response-time':'response_time','lbl-latency-web':'latency_web',
    'lbl-availability':'availability','lbl-success-checks':'successful_checks','lbl-state-changes':'state_changes',
    'lbl-outages-range':'outages_range'
  };
  for(const [id,key] of Object.entries(ids)){const el=q(id);if(el)el.textContent=tr(key)}
  const liveText=q('live-text'); if(liveText)liveText.textContent=tr('live');
  q('theme-label').textContent=document.body.classList.contains('light')?tr('dark'):tr('light');
  q('graph-close').setAttribute('aria-label',tr('close'));
  q('lang-en')?.classList.toggle('active',LANG==='en');
  q('lang-cs')?.classList.toggle('active',LANG==='cs');
  q('lang-switch')?.setAttribute('aria-label',tr('language'));
  if(q('settings-label'))q('settings-label').textContent=tr('settings');
  if(q('settings-kicker'))q('settings-kicker').textContent=tr('configuration');
  if(q('settings-title'))q('settings-title').textContent=tr('runtime_settings');
  if(q('settings-help'))q('settings-help').textContent=tr('settings_help');
  if(q('settings-save'))q('settings-save').textContent=tr('save_apply');
  if(q('settings-defaults'))q('settings-defaults').textContent=tr('use_defaults');
  if(q('settings-restart'))q('settings-restart').textContent=tr('restart_monitor');
  if(q('settings-tab-runtime'))q('settings-tab-runtime').textContent=tr('runtime_tab');
  if(q('settings-tab-targets'))q('settings-tab-targets').textContent=tr('target_manager');
  if(q('manager-title'))q('manager-title').textContent=tr('target_manager');
  if(q('manager-help'))q('manager-help').textContent=tr('manager_help');
  if(q('add-group'))q('add-group').textContent=tr('add_group');
  if(q('add-target'))q('add-target').textContent=tr('add_target');
  if(q('targets-save-restart'))q('targets-save-restart').textContent=tr('save_targets_restart');
  [['tm-index','index'],['tm-name','name'],['tm-type','type'],['tm-address','address'],['tm-port','port'],['tm-group','group'],['tm-options','options']].forEach(([id,k])=>{if(q(id))q(id).textContent=tr(k)});
  if(q('target-search'))q('target-search').placeholder=tr('search_targets');
  if(q('problems-only'))q('problems-only').textContent=tr('problems_only');
  if(q('settings-test-email'))q('settings-test-email').textContent=tr('test_email');
  if(q('graph-export'))q('graph-export').title=tr('export_csv');
  if(q('settings-close'))q('settings-close').setAttribute('aria-label',tr('close'));
  if(settingsActiveTab==='targets'&&targetConfigData?.targets&&q('groups-editor')&&q('targets-editor')) { renderGroupsEditor(); renderTargetEditor(); }
}
function dt(v){
  if(!v)return "—";
  const d=new Date(v);
  if(Number.isNaN(d.getTime()))return esc(v);
  return d.toLocaleString(loc(),{
    day:'2-digit',month:'2-digit',year:'numeric',
    hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false
  });
}
function tm(v){if(!v)return"—";const d=new Date(v);return Number.isNaN(d.getTime())?esc(v):d.toLocaleTimeString(loc())}
function duration(s){if(s==null)return tr("ongoing").toLowerCase();s=Math.max(0,Number(s));const h=Math.floor(s/3600),m=Math.floor((s%3600)/60),sec=Math.floor(s%60);return h?`${h}h ${m}m`:m?`${m}m ${sec}s`:`${sec}s`}
function pct(v){return v==null?"—":`${Number(v).toFixed(3)}%`}
function ms(v){return v==null?"—":`${Number(v).toFixed(2)} ms`}
function applyTheme(t){const l=t==="light";document.body.classList.toggle("light",l);q("theme-icon").textContent=l?"☾":"☀";q("theme-label").textContent=l?tr("dark"):tr("light")}
applyTheme(localStorage.getItem("ip-monitor-theme")||(matchMedia("(prefers-color-scheme: light)").matches?"light":"dark"));
q("theme-toggle").onclick=()=>{const n=document.body.classList.contains("light")?"dark":"light";localStorage.setItem("ip-monitor-theme",n);applyTheme(n); if(graphState.target) loadGraph()};
function setLanguage(lang){
  if(!I18N[lang]||LANG===lang)return;
  LANG=lang;localStorage.setItem('ip-monitor-lang',LANG);
  applyLanguage();renderTargets(latestTargets);loadEvents();if(graphState.target)loadGraph();loadStatus();
}
q('lang-en').onclick=()=>setLanguage('en');
q('lang-cs').onclick=()=>setLanguage('cs');
const grid=q("endpoint-grid"), events=q("events"), epFilter=q("endpoint-filter"), limitFilter=q("limit-filter");
let latestTargets=[];
function targetCard(x){
  const web=x.check_kind==="http", confirmed=Boolean(x.stability_confirmed), effective=Boolean(x.online), raw=Boolean(x.raw_ok);
  let stateLabel=tr('healthy').toUpperCase(), stateClass='healthy', endpointClass='healthy';
  if(!confirmed){stateLabel=tr('checking');stateClass='probing';endpointClass='probing'}
  else if(!effective){stateLabel=tr('offline');stateClass='bad';endpointClass='bad'}
  else if(!raw || Number(x.failure_window_failures||0)>0){stateLabel=tr('degraded');stateClass='degraded';endpointClass='degraded'}
  const service=web?`HTTP ${x.http_status??"—"} / TLS ${x.host?.startsWith("https://")?(x.verify_ssl?tr("verified"):tr("no_verify")):tr("n_a")}`:`${x.ping_ok?"ICMP OK":"ICMP FAIL"} / ${x.tcp_ok==null?`TCP ${tr("n_a")}`:x.tcp_ok?"TCP OK":"TCP FAIL"}`;
  const currentLabel=web?tr("current_get"):tr("current_ping"),score=x.health_score==null?"—":Number(x.health_score),level=x.health_level||"unknown";
  const phases=web?`<div class="http-phases"><div><span>DNS</span><b>${ms(x.dns_ms)}</b></div><div><span>TCP</span><b>${ms(x.tcp_connect_ms)}</b></div><div><span>TLS</span><b>${x.host?.startsWith("https://")?ms(x.tls_ms):tr("n_a")}</b></div><div><span>SERVER</span><b>${ms(x.server_response_ms)}</b></div></div>`:"";
  const anomalyRaw=String(x.anomaly_level||tr('no_data')).toUpperCase(), anomaly=localAnomaly(anomalyRaw), anomalyClass=anomalyRaw.toLowerCase().replace(' ','-');
  const baseline=x.baseline_latency_ms==null?'—':ms(x.baseline_latency_ms);
  const tlsWarn=web&&x.tls_days_left!=null&&Number(x.tls_days_left)<=Number(x.tls_expiry_warning_days??30);
  const tlsRow=web&&x.host?.startsWith('https://')?`<div class="meta-row"><span>${tr("tls_cert")}</span><b class="${tlsWarn?'warn-text':''}">${x.tls_days_left==null?'—':`${Number(x.tls_days_left).toFixed(1)} ${tr("days")}`}</b></div>`:'';
  const transient=confirmed&&effective&&!raw?`<div class="transient-warning">${tr("transient")} (${num(x.failure_window_failures)} / ${num(x.failure_window_checks)} ${tr("recent_failed")})</div>`:'';
  const predScore=x.prediction_score_15m==null?'—':Number(x.prediction_score_15m),predLevel=x.prediction_level_15m||'unknown';
  const phLevel=String(x.path_health_level||'LEARNING').toUpperCase(),phScore=x.path_health_score==null?'—':Number(x.path_health_score);
  const phReasons=(x.path_health_reasons||[]).map(localSummary).join(' · ');
  const pathHealth=`<div class="path-health-panel ${phLevel.toLowerCase()}"><div><label>${LANG==='cs'?'AKTIVNÍ KVALITA CESTY':'ACTIVE PATH HEALTH'}</label><b>${phScore}${phScore==='—'?'':' / 100'} · ${esc(phLevel==='NORMAL'?(LANG==='cs'?'NORMÁLNÍ':'NORMAL'):phLevel==='WATCH'?(LANG==='cs'?'SLEDOVAT':'WATCH'):phLevel==='DEGRADING'?(LANG==='cs'?'ZHORŠOVÁNÍ':'DEGRADING'):phLevel==='CRITICAL'?(LANG==='cs'?'KRITICKÁ':'CRITICAL'):(LANG==='cs'?'UČENÍ':'LEARNING'))}</b><p>${phReasons?esc(phReasons):x.path_health_observed_at?(LANG==='cs'?'Poslední aktivní test bez problémů · ':'Last active probe clean · ')+tm(x.path_health_observed_at):(LANG==='cs'?'Čekám na první krátký aktivní test.':'Waiting for first short active probe.')}</p></div><span>${x.path_health_loss_percent==null?'—':Number(x.path_health_loss_percent).toFixed(1)+'%'} ${LANG==='cs'?'ztráta':'loss'}<small>${x.path_health_jitter_ms==null?'—':Number(x.path_health_jitter_ms).toFixed(1)+' ms'} jitter</small></span></div>${x.path_suspected_shared_issue?`<div class="ops-banner path-suspect">⚠ ${LANG==='cs'?'Podezření na společnou cestu / switch':'Suspected shared path / switch issue'} · ${Number(x.path_group_affected||0)} ${LANG==='cs'?'souvisejících zařízení ovlivněno':'correlated peers affected'}</div>`:''}`;
  const prediction=`<div class="prediction ${esc(predLevel)}"><div><label>${tr("predicted_next")}</label><b>${predScore}${predScore==='—'?'':' / 100'} · ${esc(localGrade(x.prediction_grade_15m||tr('no_data')))}</b><p>${esc(localSummary(x.prediction_summary||tr('building_trend')))}</p></div><span>${tr("risk")} ${x.prediction_risk_15m==null?'—':Number(x.prediction_risk_15m)+'%'}<small>${tr("confidence")} ${x.prediction_confidence==null?'—':Number(x.prediction_confidence)+'%'}</small></span></div>`;
  return `<article class="endpoint ${endpointClass}"><div class="ep-head"><div><div class="ep-name">${esc(x.target)}</div><small>${esc(x.host)}${!web&&x.tcp_port?":"+esc(x.tcp_port):""}</small></div><div class="state ${stateClass}">${stateLabel}</div></div><div class="experience ${esc(level)}"><div class="experience-ring"><strong>${score}</strong><small>/100</small></div><div><label>${tr("stability_ux")}</label><b>${esc(localGrade(x.health_grade||tr("no_data")))}</b><p>${esc(localSummary(x.health_summary||tr("waiting_history")))}</p></div></div>${prediction}${web?'':pathHealth}<div class="counter-grid"><div class="counter"><label>${tr("uptime")}</label><b>${pct(x.uptime_24h)}</b></div><div class="counter"><label>${tr("failure")}</label><b class="${Number(x.loss_24h||0)>0?'err':''}">${pct(x.loss_24h)}</b></div><div class="counter"><label>${tr("avg_response")}</label><b>${ms(x.avg_latency_24h)}</b></div><div class="counter"><label>${tr("jitter")}</label><b>${ms(x.jitter_24h)}</b></div></div><div class="diagnostic-grid"><div><span>${tr("loss_1m")}</span><b>${pct(x.loss_1m)}</b></div><div><span>${tr("loss_5m")}</span><b>${pct(x.loss_5m)}</b></div><div><span>${tr("loss_15m")}</span><b>${pct(x.loss_15m)}</b></div><div><span>P95 · 15M</span><b>${ms(x.p95_15m)}</b></div><div><span>P99 · 15M</span><b>${ms(x.p99_15m)}</b></div><div><span>${tr("baseline")}</span><b>${baseline}</b></div></div><div class="anomaly-row"><span>${tr("adaptive")}</span><b class="anomaly ${anomalyClass}">${esc(anomaly)}${x.anomaly_z==null?'':` · z ${Number(x.anomaly_z).toFixed(2)}`}</b></div>${phases}<div class="ep-meta"><div class="meta-row"><span>${currentLabel}</span><b>${ms(x.latency_ms)}</b></div><div class="meta-row"><span>${tr("check")}</span><b>${esc(localCheck(service))}</b></div><div class="meta-row"><span>${tr("outage_rule")}</span><b>${num(x.failure_window_failures)} / ${num(x.failure_window_checks)} ${tr("failed")} · ${tr("threshold")} ${num(x.failure_threshold||3)}</b></div><div class="meta-row"><span>${tr("consecutive")}</span><b>${num(x.consecutive_failures)}</b></div><div class="meta-row"><span>${tr("total_failures")}</span><b>${num(x.total_failures)} / ${num(x.total_checks)}</b></div><div class="meta-row"><span>${tr("state_changes")}</span><b>${num(x.total_state_changes)}</b></div><div class="meta-row"><span>${tr("last_online")}</span><b>${dt(x.last_online_at)}</b></div>${tlsRow}</div>${transient}${x.maintenance_active?`<div class="ops-banner maintenance">🛠 ${tr("maintenance")}${x.maintenance_label?` · ${esc(x.maintenance_label)}`:''}</div>`:''}${x.dependency_blockers?.length?`<div class="ops-banner dependency">⛓ ${tr("dependency_down")} · ${esc(x.dependency_blockers.join(', '))}</div>`:''}${x.flapping?`<div class="ops-banner flapping">↕ ${tr("flapping")} · ${Number(x.flap_transitions||0)} / ${Math.round(Number(x.flap_window_seconds||0)/60)}m</div>`:''}${x.content_validation?`<div class="ops-banner content">✓ ${tr("content_check")}</div>`:''}${tlsWarn?`<div class="tls-warning">⚠ ${tr("tls_expires")} ${Number(x.tls_days_left).toFixed(1)} ${tr("days")} · ${dt(x.tls_expires_at)}</div>`:''}${x.alert_sent?`<div class="alert-banner sent">✉ ${tr("alert_active")} ${dt(x.alert_condition_since)}${x.alert_escalated_at?` · ${tr("escalated")} ${dt(x.alert_escalated_at)}`:''}</div>`:x.alert_condition_active?`<div class="alert-banner pending">⚠ ${tr("degradation_timer")} ${dt(x.alert_condition_since)}</div>`:x.alert_recovering_since?`<div class="alert-banner recovering">✓ ${tr("recovery_timer")}</div>`:""}${x.last_error&&!raw?`<div class="failure">${esc(x.last_error)}</div>`:""}<button class="graph-button" data-graph-target="${esc(x.target)}">⌁ ${tr("graphs")}</button></article>`
}
function groupId(name){return 'grp-'+encodeURIComponent(name).replaceAll('%','_')}
function isProblem(x){return !x.online||!x.raw_ok||!x.stability_confirmed||Number(x.failure_window_failures||0)>0||Number(x.loss_5m||0)>0||x.flapping||x.alert_condition_active||x.alert_sent||['DEGRADING','CRITICAL'].includes(String(x.path_health_level||'').toUpperCase())||['HIGH','SEVERE'].includes(String(x.anomaly_level||'').toUpperCase())||(x.prediction_score_15m!=null&&Number(x.prediction_score_15m)<75)}
const viewFilter={text:'',problems:localStorage.getItem('ip-monitor-problems-only')==='1'};
function matchesFilter(x){if(viewFilter.problems&&!isProblem(x))return false;if(!viewFilter.text)return true;const hay=[x.target,x.host,x.group,x.last_error].map(v=>String(v??'').toLowerCase()).join(' ');return viewFilter.text.split(/\s+/).filter(Boolean).every(w=>hay.includes(w))}
function renderTargets(all){latestTargets=all;const list=all.filter(matchesFilter);const fc=q('filter-count');if(fc)fc.textContent=(viewFilter.text||viewFilter.problems)?`${tr('showing')} ${list.length} / ${all.length}`:'';const groups=new Map(),groupOrder=new Map();list.forEach(x=>{const g=x.group||tr('ungrouped');if(!groups.has(g))groups.set(g,[]);groups.get(g).push(x);const gi=Number(x.group_index);if(Number.isFinite(gi)&&!groupOrder.has(g))groupOrder.set(g,gi)});const orderedGroups=[...groups.entries()].sort((a,b)=>(groupOrder.get(a[0])??999999)-(groupOrder.get(b[0])??999999));grid.innerHTML=orderedGroups.map(([name,items])=>{const online=items.filter(x=>x.online).length,scores=items.map(x=>x.health_score).filter(v=>v!=null).map(Number),avgScore=scores.length?Math.round(scores.reduce((a,b)=>a+b,0)/scores.length):null,scoreClass=avgScore==null?'unknown':avgScore>=90?'excellent':avgScore>=75?'good':avgScore>=55?'fair':avgScore>=35?'poor':'critical',collapsed=localStorage.getItem(`ip-monitor-group:${name}`)==='collapsed';return `<section class="target-group ${collapsed?'collapsed':''}" data-group="${esc(name)}"><button class="group-head" type="button" aria-expanded="${!collapsed}"><div><span class="group-chevron">⌄</span><strong>${esc(name)}</strong><small>${targetCount(items.length)}</small></div><div class="group-head-metrics"><span class="group-score ${scoreClass}">UX ${avgScore==null?'—':avgScore}</span><div class="group-health ${online===items.length?'all-ok':online===0?'all-bad':'mixed'}"><i></i>${online} / ${items.length} ${tr('online')}</div></div></button><div class="group-grid">${items.map(targetCard).join('')}</div></section>`}).join('')||(all.length?`<div class="filter-empty">${tr('no_match')}</div>`:'');grid.querySelectorAll('.group-head').forEach(btn=>btn.onclick=()=>{const section=btn.closest('.target-group'),name=section.dataset.group,next=!section.classList.contains('collapsed');section.classList.toggle('collapsed',next);btn.setAttribute('aria-expanded',String(!next));localStorage.setItem(`ip-monitor-group:${name}`,next?'collapsed':'open')});grid.querySelectorAll('[data-graph-target]').forEach(btn=>btn.onclick=e=>{e.stopPropagation();openGraph(btn.dataset.graphTarget)});
}
function updateFilter(list){const have=new Set([...epFilter.options].map(o=>o.value));list.forEach(x=>{if(!have.has(x.target)){const o=document.createElement("option");o.value=x.target;o.textContent=x.target;epFilter.appendChild(o)}})}
async function loadStatus(){const r=await fetch('/api/status',{cache:'no-store'});if(!r.ok)throw new Error(`HTTP ${r.status}`);const d=await r.json(),list=d.targets||[],summary=d.summary||{};lastStatus=d;if(q('version-line')&&d.version)q('version-line').textContent=`IP Stability Monitor ${d.version}`;renderTargets(list);updateFilter(list);q('sum-errors').textContent=Number(summary.outages_24h||0).toLocaleString(loc());q('sum-online').textContent=`${list.filter(x=>x.online).length} / ${list.length}`;q('sum-poll').textContent=`${Number(d.poll_interval_seconds).toFixed(1)} s`;const last=summary.last_state_change;q('sum-last').textContent=last?dt(last.observed_at):'—';q('sum-last-detail').textContent=last?`${last.target} · ${localCategory(last.category)}`:tr('no_state');const out=summary.last_outage;q('sum-outage').textContent=out?out.target:'—';q('sum-outage-detail').textContent=out?`${dt(out.started_at)} · ${out.active?tr('ongoing'):duration(out.duration_seconds)}`:tr('no_outage');const pred=summary.prediction||{},ps=pred.score_15m;q('sum-prediction').textContent=ps==null?'—':`${ps} / 100`;q('sum-prediction-detail').textContent=ps==null?tr('building_model'):`${pred.at_risk_targets||0} ${tr('at_risk')} · ${pred.high_risk_targets||0} ${tr('high_risk')}`; }
async function loadEvents(){const p=new URLSearchParams({limit:limitFilter.value});if(epFilter.value)p.set('target',epFilter.value);const er=await fetch(`/api/events?${p}`,{cache:'no-store'});if(!er.ok)throw new Error(`HTTP ${er.status}`);const rows=await er.json();events.innerHTML=rows.length?rows.map(x=>`<tr><td>${dt(x.observed_at)}</td><td><b>${esc(x.target)}</b></td><td><span class="event-badge ${esc(x.category)}">${esc(localCategory(x.category))}</span></td><td>${esc(localDetail(x.detail))}</td></tr>`).join(''):`<tr><td colspan="4" class="empty">${tr("no_state_changes")}</td></tr>`}
let refreshing=false,lastStatus=null;
function setLiveState(state){const chip=document.querySelector('.live-chip'),t=q('live-text');if(!chip||!t)return;chip.classList.toggle('stale',state==='down');chip.classList.toggle('stalled',state==='stalled');t.textContent=state==='down'?tr('monitor_unreachable'):state==='stalled'?tr('collector_stalled'):tr('live')}
async function refresh(){if(refreshing)return;refreshing=true;try{await Promise.all([loadStatus(),loadEvents()]);const c=lastStatus?.summary?.collector;setLiveState(c&&c.running===false&&(lastStatus.summary.reconciliation?.age_seconds||0)>30?'stalled':'ok')}catch(e){console.error(e);setLiveState('down')}finally{refreshing=false}}
const searchEl=q('target-search'),problemsBtn=q('problems-only');
function syncProblemsBtn(){problemsBtn?.setAttribute('aria-pressed',String(viewFilter.problems))}
syncProblemsBtn();
if(searchEl)searchEl.oninput=()=>{viewFilter.text=searchEl.value.trim().toLowerCase();renderTargets(latestTargets)};
if(problemsBtn)problemsBtn.onclick=()=>{viewFilter.problems=!viewFilter.problems;try{localStorage.setItem('ip-monitor-problems-only',viewFilter.problems?'1':'0')}catch(e){}syncProblemsBtn();renderTargets(latestTargets)};
epFilter.onchange=loadEvents;limitFilter.onchange=loadEvents;
q('reset-monitor').onclick=async()=>{if(!confirm(tr('reset_confirm')))return;await fetch('/api/reset',{method:'POST'});await refresh();if(graphState.target)await loadGraph()};


const SETTINGS_FIELDS=[
 ['#section_core'],
 ['poll_interval_seconds','Poll interval (s)','Interval kontroly (s)','number',0.2],
 ['sample_interval_seconds','History sample interval (s)','Interval ukládání historie (s)','number',0.2],
 ['ping_timeout_seconds','Ping timeout (s)','Timeout pingu (s)','number',0.1],
 ['http_timeout_seconds','HTTP timeout (s)','HTTP timeout (s)','number',0.2],
 ['history_retention_days','History retention (days)','Uchování historie (dny)','number',1],
 ['event_retention_days','Event log retention (days)','Uchování protokolu událostí (dny)','number',1],
 ['#section_detection'],
 ['monitoring.failure_window_checks','Failure window checks','Počet kontrol v okně','number',3],
 ['monitoring.failure_threshold','Failures to confirm outage','Selhání pro potvrzení výpadku','number',1],
 ['monitoring.recovery_success_threshold','Successes to confirm recovery','Úspěchy pro potvrzení obnovení','number',1],
 ['#section_startup'],
 ['monitoring.startup_success_checks','Successes to verify after start','Úspěchy pro ověření po startu','number',1],
 ['monitoring.startup_failure_checks','Failures to verify after start','Selhání pro ověření po startu','number',1],
 ['monitoring.startup_alert_grace_seconds','Alert grace after start (s)','Potlačení alarmů po startu (s)','number',0],
 ['#section_baseline'],
 ['monitoring.baseline_enabled','Adaptive baseline','Adaptivní referenční hodnota','checkbox'],
 ['monitoring.baseline_time_constant_hours','Baseline time constant (h)','Časová konstanta baseline (h)','number',0.1],
 ['monitoring.baseline_min_samples','Baseline minimum samples','Minimum vzorků pro baseline','number',5],
 ['monitoring.tls_expiry_warning_days','TLS warning (days)','Varování TLS (dny)','number',0],
 ['monitoring.flapping_window_seconds','Flapping window (s)','Okno kolísání stavu (s)','number',60],
 ['monitoring.flapping_transition_threshold','Flap transitions threshold','Limit změn pro flapping','number',2],
 ['#section_path'],
 ['monitoring.path_health_enabled','Active path probes','Aktivní testy cesty','checkbox'],
 ['monitoring.path_health_interval_seconds','Probe interval (s)','Interval testu (s)','number',60],
 ['monitoring.path_health_burst_packets','Packets per probe','Paketů na test','number',3],
 ['monitoring.path_health_timeout_seconds','Probe timeout (s)','Timeout testu (s)','number',2],
 ['monitoring.path_health_loss_watch_percent','Loss → watch (%)','Ztráta → sledovat (%)','number',0],
 ['monitoring.path_health_loss_critical_percent','Loss → critical (%)','Ztráta → kritické (%)','number',0],
 ['monitoring.path_health_jitter_watch_ms','Jitter → watch (ms)','Jitter → sledovat (ms)','number',0],
 ['monitoring.path_health_baseline_ratio_watch','Latency × baseline → watch','Latence × baseline → sledovat','number',1],
 ['#section_alerts'],
 ['email_alerts.enabled','Email alerts','E-mailové alarmy','checkbox'],
 ['email_alerts.degradation_seconds','Alert after degradation (s)','Alarm po zhoršení (s)','number',1],
 ['email_alerts.recovery_seconds','Recovery confirmation (s)','Potvrzení obnovení (s)','number',1],
 ['email_alerts.reminder_seconds','Reminder interval (0 = off)','Interval připomenutí (0 = vypnuto)','number',0],
 ['email_alerts.escalation_seconds','Escalation after (0 = off)','Eskalace po (0 = vypnuto)','number',0],
 ['email_alerts.alert_on_flapping','Alert on flapping','Alarm při kolísání stavu','checkbox']
];
let settingsData=null;const settingsModal=q('settings-modal');
function renderSettings(useDefaults=false){if(!settingsData)return;const values=useDefaults?settingsData.defaults:settingsData.settings;q('settings-grid').innerHTML=SETTINGS_FIELDS.map(([key,en,cs,type,min])=>{if(key.startsWith('#'))return `<div class="setting-section">${esc(tr(key.slice(1)))}</div>`;if(!(key in values))return '';const val=values[key],label=LANG==='cs'?cs:en;const input=type==='checkbox'?`<input data-setting="${esc(key)}" type="checkbox" ${val?'checked':''}>`:`<input data-setting="${esc(key)}" type="number" step="any" min="${min??''}" value="${val??''}">`;return `<label class="setting-row"><span>${esc(label)}</span>${input}</label>`}).join('')}
async function loadSettings(){const r=await fetch('/api/config',{cache:'no-store'});if(!r.ok)throw new Error(`HTTP ${r.status}`);settingsData=await r.json();if(!LANG){LANG=settingsData.language==='cs'?'cs':'en';applyLanguage()}renderSettings(false)}
async function openSettings(){setSettingsTab('runtime');settingsModal.classList.add('open');settingsModal.setAttribute('aria-hidden','false');document.body.classList.add('modal-open');q('settings-status').textContent='';try{await loadSettings()}catch(e){q('settings-status').textContent=tr('save_failed')+': '+e.message}}
function closeSettings(){settingsModal.classList.remove('open');settingsModal.setAttribute('aria-hidden','true');document.body.classList.remove('modal-open')}
q('settings-open').onclick=openSettings;q('settings-close').onclick=closeSettings;settingsModal.querySelector('[data-settings-close]').onclick=closeSettings;q('settings-defaults').onclick=()=>renderSettings(true);
q('settings-save').onclick=async()=>{
  const settings={};
  q('settings-grid').querySelectorAll('[data-setting]').forEach(el=>{
    settings[el.dataset.setting]=el.type==='checkbox'?el.checked:Number(el.value);
  });
  q('settings-status').textContent=tr('saving');
  try{
    const r=await fetch('/api/config',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({settings})
    });
    const d=await r.json();
    if(!r.ok||!d.ok){
      throw new Error(d.error||Object.values(d.errors||{}).join(', ')||`HTTP ${r.status}`);
    }
    settingsData.settings=d.settings;
    q('settings-status').textContent=tr('saved');
    await refresh();
  }catch(e){
    q('settings-status').textContent=tr('save_failed')+': '+e.message;
  }
};

async function waitForMonitorBack(){
  const deadline=Date.now()+30000;
  await new Promise(r=>setTimeout(r,900));
  while(Date.now()<deadline){
    try{
      const r=await fetch('/api/status?restart_probe='+Date.now(),{cache:'no-store'});
      if(r.ok){
        q('settings-status').textContent=tr('back_online');
        setTimeout(()=>location.reload(),500);
        return;
      }
    }catch(e){}
    await new Promise(r=>setTimeout(r,700));
  }
  q('settings-status').textContent=tr('restart_failed');
  q('settings-restart').disabled=false;
  q('settings-save').disabled=false;
}

async function restartMonitor(){
  if(!confirm(tr('restart_confirm')))return;
  const rb=q('settings-restart');
  const sb=q('settings-save');
  rb.disabled=true;
  sb.disabled=true;
  q('settings-status').textContent=tr('restarting');
  try{
    const r=await fetch('/api/restart',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:'{}'
    });
    const d=await r.json().catch(()=>({}));
    if(!r.ok||!d.ok)throw new Error(d.error||`HTTP ${r.status}`);
    waitForMonitorBack();
  }catch(e){
    q('settings-status').textContent=tr('restart_failed')+': '+e.message;
    rb.disabled=false;
    sb.disabled=false;
  }
}
q('settings-restart').onclick=restartMonitor;
q('settings-test-email').onclick=async()=>{const b=q('settings-test-email');b.disabled=true;q('settings-status').textContent=tr('sending');try{const r=await fetch('/api/alerts/test',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});const d=await r.json().catch(()=>({}));if(!r.ok||!d.ok)throw new Error(d.error||`HTTP ${r.status}`);q('settings-status').textContent=tr('test_email_sent');loadEvents().catch(()=>{})}catch(e){q('settings-status').textContent=tr('test_email_failed')+': '+e.message}finally{b.disabled=false}};


let targetConfigData={targets:[],groups:[]};
let settingsActiveTab='runtime';
const runtimePanel=q('settings-runtime-panel'),targetsPanel=q('settings-targets-panel');
function setSettingsTab(tab){
  settingsActiveTab=tab;
  const isTargets=tab==='targets';
  runtimePanel.hidden=isTargets;targetsPanel.hidden=!isTargets;
  q('settings-tab-runtime').classList.toggle('active',!isTargets);q('settings-tab-targets').classList.toggle('active',isTargets);
  q('settings-defaults').hidden=isTargets;q('settings-test-email').hidden=isTargets;q('settings-save').hidden=isTargets;q('settings-restart').hidden=isTargets;q('targets-save-restart').hidden=!isTargets;
  if(isTargets)loadTargetManager();
}
q('settings-tab-runtime').onclick=()=>setSettingsTab('runtime');q('settings-tab-targets').onclick=()=>setSettingsTab('targets');
function normalizeGroupList(){
  const seen=new Set();targetConfigData.groups=targetConfigData.groups.map(x=>String(x||'').trim()).filter(x=>x&&!seen.has(x)&&seen.add(x));
}
function renderGroupsEditor(){
  normalizeGroupList();
  q('groups-editor').innerHTML=targetConfigData.groups.length?targetConfigData.groups.map((g,i)=>`<div class="group-edit-row"><span class="drag-index">${i+1}</span><input data-group-name="${i}" value="${esc(g)}"><button class="mini-btn" data-group-up="${i}" title="${tr('move_up')}">↑</button><button class="mini-btn" data-group-down="${i}" title="${tr('move_down')}">↓</button><button class="mini-btn danger" data-group-del="${i}">${tr('delete_word')}</button></div>`).join(''):`<div class="manager-empty">${tr('ungrouped')}</div>`;
  q('groups-editor').querySelectorAll('[data-group-name]').forEach(el=>el.onchange=()=>{const i=Number(el.dataset.groupName),old=targetConfigData.groups[i],neu=el.value.trim();if(!neu){el.value=old;return}targetConfigData.groups[i]=neu;targetConfigData.targets.forEach(t=>{if((t.group||'')===old)t.group=neu});renderTargetEditor()});
  q('groups-editor').querySelectorAll('[data-group-up]').forEach(b=>b.onclick=()=>moveGroup(Number(b.dataset.groupUp),-1));
  q('groups-editor').querySelectorAll('[data-group-down]').forEach(b=>b.onclick=()=>moveGroup(Number(b.dataset.groupDown),1));
  q('groups-editor').querySelectorAll('[data-group-del]').forEach(b=>b.onclick=()=>deleteGroup(Number(b.dataset.groupDel)));
}
function moveGroup(i,d){const j=i+d;if(j<0||j>=targetConfigData.groups.length)return;[targetConfigData.groups[i],targetConfigData.groups[j]]=[targetConfigData.groups[j],targetConfigData.groups[i]];renderGroupsEditor();renderTargetEditor()}
function deleteGroup(i){if(!confirm(tr('confirm_delete_group')))return;const g=targetConfigData.groups[i];targetConfigData.groups.splice(i,1);targetConfigData.targets.forEach(t=>{if((t.group||'')===g)delete t.group});renderGroupsEditor();renderTargetEditor()}
function groupOptions(current){return `<option value="">${tr('ungrouped')}</option>`+targetConfigData.groups.map(g=>`<option value="${esc(g)}" ${g===current?'selected':''}>${esc(g)}</option>`).join('')}
function renderTargetEditor(){
  const body=q('targets-editor');
  body.innerHTML=targetConfigData.targets.map((t,i)=>{const web=!!(t.url||(typeof t.host==='string'&&/^https?:\/\//i.test(t.host)));const endpoint=web?(t.url||t.host||''):(t.host||'');return `<tr data-target-row="${i}"><td><input class="index-input" data-field="index" type="number" min="1" value="${i+1}"></td><td><input data-field="name" value="${esc(t.name||'')}"></td><td><select data-field="kind"><option value="host" ${!web?'selected':''}>${tr('host_type')}</option><option value="web" ${web?'selected':''}>${tr('web_type')}</option></select></td><td><input data-field="endpoint" value="${esc(endpoint)}" placeholder="${web?'https://example/':'10.0.0.1'}"></td><td><input data-field="tcp_port" type="number" min="1" max="65535" value="${t.tcp_port??''}" ${web?'disabled':''}></td><td><select data-field="group">${groupOptions(t.group||'')}</select></td><td class="target-options">${web?`<label><input data-field="verify_ssl" type="checkbox" ${t.verify_ssl!==false?'checked':''}> ${tr('verify_ssl_short')}</label><input data-field="expected_status" value="${esc(t.expected_status??'200-399')}" title="${tr('expected_status_short')}">`:'—'}</td><td class="target-actions"><button class="mini-btn" data-up="${i}" title="${tr('move_up')}">↑</button><button class="mini-btn" data-down="${i}" title="${tr('move_down')}">↓</button><button class="mini-btn danger" data-del="${i}">${tr('delete_word')}</button></td></tr>`}).join('');
  body.querySelectorAll('tr').forEach(row=>wireTargetRow(row));
  body.querySelectorAll('[data-up]').forEach(b=>b.onclick=()=>moveTarget(Number(b.dataset.up),-1));body.querySelectorAll('[data-down]').forEach(b=>b.onclick=()=>moveTarget(Number(b.dataset.down),1));body.querySelectorAll('[data-del]').forEach(b=>b.onclick=()=>deleteTarget(Number(b.dataset.del)));
}
function wireTargetRow(row){
  const i=Number(row.dataset.targetRow), t=targetConfigData.targets[i];
  row.querySelectorAll('[data-field]').forEach(el=>{
    el.onchange=()=>{
      const f=el.dataset.field;
      if(f==='index'){
        const dest=Math.max(1,Math.min(targetConfigData.targets.length,Number(el.value)||i+1))-1;
        if(dest!==i){const [x]=targetConfigData.targets.splice(i,1);targetConfigData.targets.splice(dest,0,x);renderTargetEditor()}
        return;
      }
      if(f==='kind'){
        const endpoint=row.querySelector('[data-field="endpoint"]').value.trim();
        if(el.value==='web'){
          delete t.host;t.url=/^https?:\/\//i.test(endpoint)?endpoint:`https://${endpoint}`;delete t.tcp_port;
          if(t.verify_ssl===undefined)t.verify_ssl=true;if(t.expected_status===undefined)t.expected_status='200-399';
        }else{
          t.host=endpoint.replace(/^https?:\/\//i,'');delete t.url;delete t.verify_ssl;delete t.expected_status;
        }
        renderTargetEditor();return;
      }
      if(f==='name'){const old=t.name,neu=el.value.trim();t.name=neu;if(old&&neu&&old!==neu)targetConfigData.targets.forEach(other=>{if(Array.isArray(other.depends_on))other.depends_on=other.depends_on.map(d=>d===old?neu:d);else if(other.depends_on===old)other.depends_on=neu})}
      else if(f==='endpoint'){if(t.url!==undefined)t.url=el.value.trim();else t.host=el.value.trim()}
      else if(f==='tcp_port'){if(el.value)t.tcp_port=Number(el.value);else delete t.tcp_port}
      else if(f==='group'){if(el.value)t.group=el.value;else delete t.group}
      else if(f==='verify_ssl')t.verify_ssl=el.checked;
      else if(f==='expected_status'){if(el.value)t.expected_status=el.value.trim();else delete t.expected_status}
    };
  });
}

function moveTarget(i,d){const j=i+d;if(j<0||j>=targetConfigData.targets.length)return;[targetConfigData.targets[i],targetConfigData.targets[j]]=[targetConfigData.targets[j],targetConfigData.targets[i]];renderTargetEditor()}
function deleteTarget(i){if(!confirm(tr('confirm_delete_target')))return;const removed=targetConfigData.targets[i]?.name;targetConfigData.targets.splice(i,1);if(removed)targetConfigData.targets.forEach(t=>{if(Array.isArray(t.depends_on)){t.depends_on=t.depends_on.filter(d=>d!==removed);if(!t.depends_on.length)delete t.depends_on}else if(t.depends_on===removed)delete t.depends_on});renderTargetEditor()}
q('add-group').onclick=()=>{let base=LANG==='cs'?'Nová skupina':'New group',name=base,n=2;while(targetConfigData.groups.includes(name))name=`${base} ${n++}`;targetConfigData.groups.push(name);renderGroupsEditor();renderTargetEditor()};
q('add-target').onclick=()=>{let base=LANG==='cs'?'Nové zařízení':'New target',name=base,n=2,names=new Set(targetConfigData.targets.map(t=>t.name));while(names.has(name))name=`${base} ${n++}`;targetConfigData.targets.push({name,host:'0.0.0.0'});renderTargetEditor()};
async function loadTargetManager(){try{const r=await fetch('/api/targets-config',{cache:'no-store'});const d=await r.json();if(!r.ok)throw new Error(d.error||`HTTP ${r.status}`);targetConfigData={targets:Array.isArray(d.targets)?d.targets:[],groups:Array.isArray(d.groups)?d.groups:[]};renderGroupsEditor();renderTargetEditor()}catch(e){q('settings-status').textContent=tr('targets_save_failed')+': '+e.message}}
async function saveTargetsAndRestart(){const btn=q('targets-save-restart');btn.disabled=true;q('settings-status').textContent=tr('saving');try{const r=await fetch('/api/targets-config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(targetConfigData)});const d=await r.json();if(!r.ok||!d.ok)throw new Error(d.error||`HTTP ${r.status}`);q('settings-status').textContent=tr('targets_saved');const rr=await fetch('/api/restart',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});const rd=await rr.json().catch(()=>({}));if(!rr.ok||!rd.ok)throw new Error(rd.error||`HTTP ${rr.status}`);waitForMonitorBack()}catch(e){q('settings-status').textContent=tr('targets_save_failed')+': '+e.message;btn.disabled=false}}
q('targets-save-restart').onclick=saveTargetsAndRestart;
const graphState={target:null,range:'24h'};
const modal=q('graph-modal');
function openGraph(target){graphState.target=target;const t=latestTargets.find(x=>x.target===target);q('graph-title').textContent=target;q('graph-endpoint').textContent=t?.host||'—';updateExportLink();modal.classList.add('open');modal.setAttribute('aria-hidden','false');document.body.classList.add('modal-open');loadGraph()}
function closeGraph(){modal.classList.remove('open');modal.setAttribute('aria-hidden','true');document.body.classList.remove('modal-open');graphState.target=null}
q('graph-close').onclick=closeGraph;modal.querySelector('.modal-backdrop').onclick=closeGraph;document.addEventListener('keydown',e=>{if(e.key!=='Escape')return;if(modal.classList.contains('open'))closeGraph();else if(settingsModal.classList.contains('open'))closeSettings()});
function updateExportLink(){const a=q('graph-export');if(a&&graphState.target)a.href=`/api/export/${encodeURIComponent(graphState.target)}.csv?range=${graphState.range}`}
q('range-tabs').querySelectorAll('button').forEach(b=>b.onclick=()=>{q('range-tabs').querySelectorAll('button').forEach(x=>x.classList.remove('active'));b.classList.add('active');graphState.range=b.dataset.range;updateExportLink();loadGraph()});

function chartColors(){const s=getComputedStyle(document.body);return {text:s.getPropertyValue('--text').trim(),muted:s.getPropertyValue('--muted').trim(),border:s.getPropertyValue('--border').trim(),green:s.getPropertyValue('--green').trim(),red:s.getPropertyValue('--red').trim(),cyan:s.getPropertyValue('--cyan').trim()}}
function fmtAxisTime(v,range){const d=new Date(v);if(range==='1h'||range==='6h'||range==='24h')return d.toLocaleTimeString(loc(),{hour:'2-digit',minute:'2-digit'});if(range==='7d')return d.toLocaleDateString(loc(),{weekday:'short',hour:'2-digit'});return d.toLocaleDateString(loc(),{month:'short',day:'numeric'})}
function graphPointBudget(){const w=Math.max(280,Math.min(window.innerWidth||1000,1200));return w<480?90:w<760?140:w<1100?220:320}
function thinLinePoints(points,key,maxPoints=graphPointBudget()){if(points.length<=maxPoints)return points;const out=[],bucket=Math.max(1,Math.ceil(points.length/maxPoints));for(let i=0;i<points.length;i+=bucket){const chunk=points.slice(i,i+bucket),valid=chunk.filter(p=>p[key]!=null&&Number.isFinite(Number(p[key])));if(!valid.length){out.push(chunk[Math.floor(chunk.length/2)]);continue}let lo=valid[0],hi=valid[0];for(const p of valid){if(Number(p[key])<Number(lo[key]))lo=p;if(Number(p[key])>Number(hi[key]))hi=p}for(const p of [lo,hi].sort((a,b)=>points.indexOf(a)-points.indexOf(b)))if(out[out.length-1]!==p)out.push(p)}return out}
function thinAvailability(points,maxPoints=graphPointBudget()){if(points.length<=maxPoints)return points;const out=[],bucket=Math.max(1,Math.ceil(points.length/maxPoints));for(let i=0;i<points.length;i+=bucket){const c=points.slice(i,i+bucket),checks=c.reduce((a,p)=>a+Number(p.checks||0),0),weighted=c.reduce((a,p)=>a+Number(p.availability||0)*Number(p.checks||0),0);out.push({...c[c.length-1],availability:checks?weighted/checks:0,checks})}return out}
function chartWidth(el){return Math.max(320,Math.round(el.getBoundingClientRect().width||700))}
function lineChart(el,points,key,opts={}){points=thinLinePoints(points,key);if(!points.length){el.innerHTML=`<div class="chart-empty">${tr('no_samples')}</div>`;return}const c=chartColors(),W=chartWidth(el),mobile=W<520,H=mobile?210:270,L=mobile?42:58,R=mobile?8:18,T=18,B=mobile?32:38,iw=W-L-R,ih=H-T-B;const vals=points.map(p=>p[key]).filter(v=>v!==null&&v!==undefined&&Number.isFinite(Number(v))).map(Number);if(!vals.length){el.innerHTML=`<div class="chart-empty">${tr('no_response_samples')}</div>`;return}let min=opts.min??Math.min(...vals),max=opts.max??Math.max(...vals);if(max===min){max=min+1}if(opts.zeroBase)min=0;const pad=opts.pad??Math.max((max-min)*.12,1);if(opts.min==null&&!opts.zeroBase)min=Math.max(0,min-pad);if(opts.max==null)max=max+pad;const x=i=>L+(points.length===1?iw/2:i*iw/(points.length-1)),y=v=>T+(max-v)*ih/(max-min);let path='',dots='';points.forEach((p,i)=>{const v=p[key];if(v==null)return;const xx=x(i),yy=y(Number(v));path+=`${path?' L':'M'} ${xx.toFixed(2)} ${yy.toFixed(2)}`;});const grid=[0,.25,.5,.75,1].map(f=>{const yy=T+ih*f,val=max-(max-min)*f;return `<line x1="${L}" y1="${yy}" x2="${W-R}" y2="${yy}" class="gridline"/><text x="${L-9}" y="${yy+4}" text-anchor="end" class="axistext">${opts.formatY?opts.formatY(val):val.toFixed(0)}</text>`}).join('');const ticks=[0,.25,.5,.75,1].map(f=>{const i=Math.min(points.length-1,Math.round((points.length-1)*f)),xx=x(i);return `<text x="${xx}" y="${H-10}" text-anchor="middle" class="axistext">${esc(fmtAxisTime(points[i].observed_at,graphState.range))}</text>`}).join('');
const outages=points.map((p,i)=>p.availability<100?`<rect x="${Math.max(L,x(i)-2)}" y="${T}" width="4" height="${ih}" class="outage-mark"/>`:'' ).join('');el.innerHTML=`<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet" role="img">${grid}${outages}<path d="${path}" class="chartline"/><line x1="${L}" y1="${T+ih}" x2="${W-R}" y2="${T+ih}" class="axisline"/>${ticks}</svg>`}
function availabilityChart(el,points){points=thinAvailability(points);if(!points.length){el.innerHTML=`<div class="chart-empty">${tr('no_samples')}</div>`;return}const c=chartColors(),W=chartWidth(el),mobile=W<520,H=mobile?190:230,L=mobile?42:58,R=mobile?8:18,T=15,B=mobile?32:38,iw=W-L-R,ih=H-T-B;const bw=Math.max(1,iw/points.length);const ticks=[100,75,50,25,0].map(v=>{const yy=T+(100-v)*ih/100;return `<line x1="${L}" y1="${yy}" x2="${W-R}" y2="${yy}" class="gridline"/><text x="${L-9}" y="${yy+4}" text-anchor="end" class="axistext">${v}%</text>`}).join('');const bars=points.map((p,i)=>{const v=Math.max(0,Math.min(100,Number(p.availability||0))),h=ih*v/100,xx=L+i*bw,yy=T+ih-h;return `<rect x="${xx}" y="${yy}" width="${Math.max(.8,bw+.25)}" height="${h}" class="${v>=100?'avail-ok':'avail-bad'}"><title>${fmtAxisTime(p.observed_at,graphState.range)} · ${v.toFixed(2)}%</title></rect>`}).join('');const xt=[0,.25,.5,.75,1].map(f=>{const i=Math.min(points.length-1,Math.round((points.length-1)*f)),xx=L+i*bw+bw/2;return `<text x="${xx}" y="${H-10}" text-anchor="middle" class="axistext">${esc(fmtAxisTime(points[i].observed_at,graphState.range))}</text>`}).join('');el.innerHTML=`<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet">${ticks}${bars}<line x1="${L}" y1="${T+ih}" x2="${W-R}" y2="${T+ih}" class="axisline"/>${xt}</svg>`}
function rangeLabel(s){
  s=Number(s)||0;
  if(s<60)return LANG==='cs'?`${s} s`:`${s}s`;
  if(s<3600)return LANG==='cs'?`${Math.round(s/60)} min`:`${Math.round(s/60)}m`;
  return LANG==='cs'?`${Math.round(s/3600)} h`:`${Math.round(s/3600)}h`;
}
async function loadGraph(){if(!graphState.target)return;const target=graphState.target,range=graphState.range;q('latency-chart').innerHTML=`<div class="chart-loading">${tr('loading_history')}</div>`;q('availability-chart').innerHTML='';try{const r=await fetch(`/api/history/${encodeURIComponent(target)}?range=${range}`,{cache:'no-store'});if(!r.ok)throw new Error(`HTTP ${r.status}`);const d=await r.json();if(graphState.target!==target||graphState.range!==range)return;const pts=d.points||[],lat=pts.map(p=>p.latency_ms).filter(v=>v!=null).map(Number),checks=pts.reduce((a,p)=>a+Number(p.checks||0),0),weighted=pts.reduce((a,p)=>a+Number(p.availability||0)*Number(p.checks||0),0),availability=checks?weighted/checks:null,web=pts.some(p=>p.check_kind==='http');const avg=k=>{const v=pts.map(p=>p[k]).filter(x=>x!=null).map(Number);return v.length?v.reduce((a,b)=>a+b,0)/v.length:null};const phaseSummary=web?`<div><small>${tr("avg_dns")}</small><strong>${ms(avg('dns_ms'))}</strong></div><div><small>${tr("avg_tcp")}</small><strong>${ms(avg('tcp_connect_ms'))}</strong></div><div><small>${tr("avg_tls")}</small><strong>${ms(avg('tls_ms'))}</strong></div><div><small>${tr("avg_server")}</small><strong>${ms(avg('server_response_ms'))}</strong></div>`:'';const hs=d.summary||{};q('graph-summary').innerHTML=`<div><small>${tr("range_availability")}</small><strong>${availability==null?'—':availability.toFixed(3)+'%'}</strong></div><div><small>${tr("avg_total_response")}</small><strong>${lat.length?(lat.reduce((a,b)=>a+b,0)/lat.length).toFixed(2)+' ms':'—'}</strong></div><div><small>${tr("p95p99")}</small><strong>${ms(hs.p95_latency_ms)} / ${ms(hs.p99_latency_ms)}</strong></div><div><small>${tr("samples_resolution")}</small><strong>${checks.toLocaleString(loc())} · ${rangeLabel(d.bucket_seconds)}</strong></div>${phaseSummary}`;q('latency-latest').textContent=lat.length?`${lat[lat.length-1].toFixed(2)} ms`:'—';q('availability-latest').textContent=availability==null?'—':`${availability.toFixed(3)}%`;lineChart(q('latency-chart'),pts,'latency_ms',{formatY:v=>`${v.toFixed(0)} ms`});availabilityChart(q('availability-chart'),pts);const ev=d.events||[];q('graph-events').innerHTML=ev.length?ev.slice().reverse().map(e=>`<div class="mini-event"><span class="event-badge ${esc(e.category)}">${esc(localCategory(e.category))}</span><b>${dt(e.observed_at)}</b><p>${esc(localDetail(e.detail))}</p></div>`).join(''):`<div class="chart-empty">${tr("no_outages_range")}</div>`}catch(e){console.error(e);q('latency-chart').innerHTML=`<div class="chart-empty">${tr("graph_error")}: ${esc(e.message)}</div>`;q('availability-chart').innerHTML=''}}

let graphResizeTimer=null;window.addEventListener('resize',()=>{if(!graphState.target)return;clearTimeout(graphResizeTimer);graphResizeTimer=setTimeout(()=>loadGraph(),180)},{passive:true});

// Start only after the complete script (including Targets & Groups state) is initialized.
async function initializeDashboard(){
  if(!LANG){
    try{
      const r=await fetch('/api/config',{cache:'no-store'});
      const d=await r.json();
      LANG=d.language==='cs'?'cs':'en';
    }catch(e){
      LANG=(navigator.language||'en').toLowerCase().startsWith('cs')?'cs':'en';
    }
  }
  applyLanguage();
  q('clock').textContent=new Date().toLocaleTimeString(loc());
  setInterval(()=>q('clock').textContent=new Date().toLocaleTimeString(loc()),250);
  await refresh();
  setInterval(refresh,2000);
}
initializeDashboard().catch(e=>{
  console.error('Dashboard initialization failed',e);
  const grid=q('endpoint-grid');
  if(grid)grid.innerHTML=`<div class="dashboard-error">Dashboard initialization failed: ${esc(e.message||String(e))}</div>`;
});

