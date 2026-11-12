/* Selector de modo claro / oscuro, compartido por todas las páginas. */
(function(){
  var root=document.documentElement,tb=document.getElementById("theme"),avisos=[];
  var SUN='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4.5"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>';
  var MOON='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/></svg>';
  function isDark(){var t=root.getAttribute("data-theme");return t?t==="dark":window.matchMedia("(prefers-color-scheme: dark)").matches}
  function paint(){var d=isDark();tb.innerHTML=d?SUN:MOON;tb.setAttribute("aria-label",d?"Cambiar a modo claro":"Cambiar a modo oscuro")}
  try{var saved=localStorage.getItem("obaq-theme");if(saved)root.setAttribute("data-theme",saved)}catch(e){}
  tb.onclick=function(){var next=isDark()?"light":"dark";root.setAttribute("data-theme",next);try{localStorage.setItem("obaq-theme",next)}catch(e){}paint();avisos.forEach(function(f){f()})};
  paint();
  window.OBAQ={isDark:isDark,alCambiarTema:function(f){avisos.push(f)},
    esc:function(s){return String(s==null?"":s).replace(/[&<>"']/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]})}};
})();
