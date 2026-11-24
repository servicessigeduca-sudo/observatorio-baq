/* Panel de revisión de casos: lee data/casos.json del repositorio con la clave
   de GitHub de quien revisa y guarda sus decisiones en un solo commit. */
(function(global){
  "use strict";
  var REPO="servicessigeduca-sudo/observatorio-baq", RAMA="main";
  var API="https://api.github.com/repos/"+REPO+"/contents/";
  var CLAVE_LS="obaq-revisar-clave";
  var TIPOS=["homicidio","feminicidio","lesiones","hurto","extorsion","secuestro","violencia_sexual","violencia_intrafamiliar","desaparicion"];
  var NOMBRE_TIPO={homicidio:"Homicidio",feminicidio:"Feminicidio",lesiones:"Lesiones",hurto:"Hurto",extorsion:"Extorsión",secuestro:"Secuestro",violencia_sexual:"Violencia sexual",violencia_intrafamiliar:"Violencia intrafamiliar",desaparicion:"Desaparición"};
  var MUNICIPIOS=["Barranquilla","Soledad","Malambo","Galapa","Puerto Colombia"];
  var EDITABLES=["tipo","municipio","barrio","fecha"];

  /* ---------- Lógica pura (también la usan las pruebas) ---------- */

  function revisado(c){ return c.estado==="publicado"||c.estado==="descartado"||!!c.revisado_por; }

  function unirListas(a,b){ var r=(a||[]).slice(); (b||[]).forEach(function(x){ if(r.indexOf(x)<0) r.push(x); }); return r; }

  /* cambios: {caso_id: {estado?, tipo?, municipio?, barrio?, fecha?, unir_con?}}.
     Se aplican sobre la versión más reciente del archivo, por caso_id, para no
     pisar lo que el scraper haya guardado mientras tanto. */
  function aplicar(casos, cambios, quien, hoy){
    var porId={}; casos.forEach(function(c){ porId[c.caso_id]=c; });
    var quitar={}, aplicados=0, faltan=[];
    Object.keys(cambios).forEach(function(id){
      var c=porId[id], ch=cambios[id];
      if(!c||quitar[id]){ faltan.push(id); return; }
      if(ch.unir_con){
        var o=porId[ch.unir_con];
        if(!o||quitar[ch.unir_con]){ faltan.push(id); return; }
        // Este caso pasa a ser parte del otro: el otro conserva su id.
        o.notas=unirListas(o.notas,c.notas).sort();
        o.medios=unirListas(o.medios,c.medios).sort();
        o.tipos=unirListas(o.tipos,c.tipos);
        var urls=(o.fuentes||[]).map(function(f){ return f.url; });
        (c.fuentes||[]).forEach(function(f){ if(urls.indexOf(f.url)<0) o.fuentes.push(f); });
        if(c.fecha&&(!o.fecha||c.fecha<o.fecha)) o.fecha=c.fecha;
        if(!o.barrio&&c.barrio) o.barrio=c.barrio;
        o.posible_duplicado_de=(o.posible_duplicado_de||[]).filter(function(x){ return x!==id; });
        if(o.estado==="posible_duplicado"&&!o.posible_duplicado_de.length) o.estado="pendiente";
        o.revisado_por=quien; o.revisado_en=hoy;
        quitar[id]=true; aplicados++;
        return;
      }
      EDITABLES.forEach(function(k){ if(k in ch) c[k]=ch[k]===""?null:ch[k]; });
      if(ch.estado==="pendiente"){
        c.estado=(c.posible_duplicado_de||[]).length?"posible_duplicado":"pendiente";
        delete c.revisado_por; delete c.revisado_en;
      }else{
        if(ch.estado) c.estado=ch.estado;
        c.revisado_por=quien; c.revisado_en=hoy;
      }
      if(c.tipo&&(c.tipos||[]).indexOf(c.tipo)<0) c.tipos=[c.tipo].concat(c.tipos||[]);
      aplicados++;
    });
    var fuera=Object.keys(quitar);
    casos=casos.filter(function(c){ return !quitar[c.caso_id]; });
    casos.forEach(function(c){
      if(c.posible_duplicado_de) c.posible_duplicado_de=c.posible_duplicado_de.filter(function(x){ return fuera.indexOf(x)<0; });
    });
    return {casos:casos, aplicados:aplicados, faltan:faltan};
  }

  function aJson(casos){ return JSON.stringify(casos,null,2)+"\n"; }

  global.RV={aplicar:aplicar, aJson:aJson, revisado:revisado};
  if(typeof document==="undefined") return;

  /* ---------- Página ---------- */

  var $=function(id){ return document.getElementById(id); };
  var esc=function(s){ return String(s==null?"":s).replace(/[&<>"']/g,function(m){ return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[m]; }); };
  var clave=null, usuario=null, casos=[], notas={}, barrios=[], cambios={}, vista="pendientes";

  function leerLS(){ try{ return localStorage.getItem(CLAVE_LS); }catch(e){ return null; } }
  function guardarLS(v){ try{ v?localStorage.setItem(CLAVE_LS,v):localStorage.removeItem(CLAVE_LS); }catch(e){} }

  function gh(url,opc){
    opc=opc||{}; opc.headers=Object.assign({"Authorization":"Bearer "+clave,"X-GitHub-Api-Version":"2022-11-28"},opc.headers||{});
    return fetch(url,opc).then(function(r){
      if(!r.ok) return r.text().then(function(t){ var e=new Error(r.status+" "+t.slice(0,200)); e.status=r.status; throw e; });
      return r;
    });
  }
  function leerArchivo(ruta){
    // sha (para guardar) y contenido crudo (el JSON puede pasar de 1 MB).
    return Promise.all([
      gh(API+ruta+"?ref="+RAMA,{headers:{"Accept":"application/vnd.github.object+json"}}).then(function(r){ return r.json(); }),
      gh(API+ruta+"?ref="+RAMA+"&t="+Date.now(),{headers:{"Accept":"application/vnd.github.raw+json"},cache:"no-store"}).then(function(r){ return r.json(); })
    ]).then(function(x){ return {sha:x[0].sha, datos:x[1]}; });
  }
  function b64(texto){
    var bytes=new TextEncoder().encode(texto), s="";
    for(var i=0;i<bytes.length;i+=0x8000) s+=String.fromCharCode.apply(null,bytes.subarray(i,i+0x8000));
    return btoa(s);
  }

  function entrar(v){
    clave=v; $("msg-login").className="rv-msg"; $("msg-login").textContent="Comprobando la clave…";
    return gh("https://api.github.com/repos/"+REPO).then(function(r){ return r.json(); }).then(function(repo){
      if(!repo.permissions||!repo.permissions.push) throw new Error("La clave no tiene permiso de escritura en el repositorio.");
      return gh("https://api.github.com/user").then(function(r){ return r.json(); }).catch(function(){ return {}; });
    }).then(function(u){
      usuario=u.login||"panel";
      if($("recordar").checked) guardarLS(clave);
      return cargar();
    }).then(function(){
      $("s-login").hidden=true; $("s-panel").hidden=false;
    }).catch(function(e){
      clave=null;
      $("msg-login").className="rv-msg err";
      $("msg-login").textContent=e.status===401?"GitHub no reconoce la clave. Revisa que la copiaste completa y que no haya vencido.":(e.message||"No se pudo entrar.");
    });
  }

  function cargar(){
    $("conteo").textContent="Cargando casos…";
    return Promise.all([
      leerArchivo("data/casos.json"),
      leerArchivo("data/notas.json").catch(function(){ return {datos:[]}; }),
      leerArchivo("data/geocodigos.json").catch(function(){ return {datos:{}}; }),
      // Lista única de barrios (la publica el sitio): se sugieren primero estos nombres.
      fetch("data/publico/barrios.csv").then(function(r){ return r.ok?r.text():""; }).catch(function(){ return ""; })
    ]).then(function(x){
      casos=x[0].datos;
      notas={}; (x[1].datos||[]).forEach(function(n){ notas[n.id]=n; });
      var vistos={}; barrios=[];
      (x[3]||"").split("\n").slice(1).forEach(function(l){ var c=l.split(","); if(c.length>=3&&c[1]&&!vistos[c[1]]){ vistos[c[1]]=1; barrios.push(c[1]); } });
      Object.keys(x[2].datos||{}).forEach(function(k){ var b=k.split("|")[0]; var g=x[2].datos[k]||{}, n=g.nombre_osm?g.nombre_osm.split(",")[0]:b.replace(/\b\w/g,function(l){ return l.toUpperCase(); }); if(!vistos[n]){ vistos[n]=1; barrios.push(n); } });
      casos.forEach(function(c){ if(c.barrio&&!vistos[c.barrio]){ vistos[c.barrio]=1; barrios.push(c.barrio); } });
      barrios.sort(function(a,b){ return a.localeCompare(b,"es"); });
      pintar();
    });
  }

  function estadoVisto(c){ var ch=cambios[c.caso_id]; return ch&&ch.estado?ch.estado:c.estado; }
  function valor(c,k){ var ch=cambios[c.caso_id]; return ch&&(k in ch)?ch[k]:c[k]; }
  function enVista(c){
    var e=estadoVisto(c), rev=cambios[c.caso_id]?e!=="pendiente"&&e!=="posible_duplicado":revisado(c);
    if(vista==="pendientes") return !rev||!!cambios[c.caso_id];
    if(vista==="duplicados") return c.estado==="posible_duplicado";
    if(vista==="revisados") return rev;
    return true;
  }
  function coincide(c){
    var q=$("buscar").value.trim().toLowerCase(), t=$("f-tipo").value;
    if(t&&valor(c,"tipo")!==t) return false;
    if(!q) return true;
    var txt=[c.barrio,c.municipio,(c.medios||[]).join(" ")].concat((c.fuentes||[]).map(function(f){ return f.titular; })).join(" ").toLowerCase();
    return txt.indexOf(q)>=0;
  }
  function resumenDe(c){
    for(var i=0;i<(c.notas||[]).length;i++){ var n=notas[c.notas[i]]; if(n&&n.resumen) return n.resumen; }
    return "";
  }
  function titularDe(id){ var o=casos.filter(function(c){ return c.caso_id===id; })[0]; return o&&o.fuentes&&o.fuentes[0]?o.fuentes[0].titular:id; }

  function etiquetaEstado(e){
    return {publicado:'<span class="rv-et pub">Publicado</span>',descartado:'<span class="rv-et des">Descartado</span>',posible_duplicado:'<span class="rv-et dup">Posible duplicado</span>',pendiente:'<span class="rv-et">Sin revisar</span>'}[e]||"";
  }

  function tarjeta(c){
    var id=c.caso_id, ch=cambios[id]||{}, e=estadoVisto(c), tipo=valor(c,"tipo");
    var opTipo=TIPOS.concat(TIPOS.indexOf(tipo)<0&&tipo?[tipo]:[]).map(function(t){ return '<option value="'+t+'"'+(t===tipo?" selected":"")+'>'+esc(NOMBRE_TIPO[t]||t)+'</option>'; }).join("");
    var muni=valor(c,"municipio")||"";
    var opMuni='<option value="">Sin municipio</option>'+MUNICIPIOS.map(function(m){ return '<option'+(m===muni?" selected":"")+'>'+m+'</option>'; }).join("");
    var fuentes=(c.fuentes||[]).map(function(f){
      return '<li><a href="'+esc(f.url)+'" target="_blank" rel="noopener">'+esc(f.titular||f.url)+'</a><small>'+esc(f.medio)+'</small></li>';
    }).join("");
    var res=resumenDe(c);
    var mapa=c.lat!=null?' · <a href="https://www.openstreetmap.org/?mlat='+c.lat+'&mlon='+c.lon+'#map=16/'+c.lat+'/'+c.lon+'" target="_blank" rel="noopener">Ver en el mapa</a>':"";
    var dups=(c.posible_duplicado_de||[]).filter(function(o){ return casos.some(function(x){ return x.caso_id===o; }); });
    var bloqueDup=dups.length&&!ch.unir_con?'<div class="rv-dup"><span>¿Es el mismo hecho que…?</span>'+dups.map(function(o){
      return '<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center"><span style="flex:1 1 220px">'+esc(titularDe(o))+'</span><button type="button" class="rv-b" data-acc="unir" data-con="'+o+'">Sí, unir</button></div>';
    }).join("")+'<span class="rv-msg">Si son hechos distintos, publícalo normalmente.</span></div>':"";
    var unido=ch.unir_con?'<div class="rv-dup"><b>Se unirá al caso:</b> '+esc(titularDe(ch.unir_con))+'</div>':"";
    return '<article class="rv-caso'+(cambios[id]?" cambiado":"")+'" data-id="'+id+'">'+
      '<div class="rv-cab"><span class="rv-et'+(tipo==="homicidio"||tipo==="feminicidio"?" hom":"")+'">'+esc(NOMBRE_TIPO[tipo]||tipo)+'</span><b>'+esc(valor(c,"fecha")||"Sin fecha")+'</b><span>'+esc([valor(c,"barrio"),muni].filter(Boolean).join(", ")||"Sin ubicación")+'</span>'+etiquetaEstado(ch.unir_con?"":e)+(c.varios_hechos?'<span class="rv-et dup" title="La nota parece contar más de un hecho: sepáralos si es así">Varios hechos</span>':'')+'</div>'+
      '<ul class="rv-fuentes">'+fuentes+'</ul>'+
      (res?'<p class="rv-msg">'+esc(res)+'</p>':"")+
      '<p class="rv-msg">'+esc((c.medios||[]).length)+' medio(s) · Ubicación: '+esc(c.confianza_ubicacion||"sin ubicar")+mapa+'</p>'+
      unido+
      (ch.unir_con?"":'<div class="rv-campos">'+
        '<label>Tipo<select data-k="tipo">'+opTipo+'</select></label>'+
        '<label>Municipio<select data-k="municipio">'+opMuni+'</select></label>'+
        '<label>Barrio<input data-k="barrio" list="dl-barrios" value="'+esc(valor(c,"barrio")||"")+'" placeholder="Sin barrio"></label>'+
        '<label>Fecha<input type="date" data-k="fecha" value="'+esc(valor(c,"fecha")||"")+'"></label>'+
      '</div>'+bloqueDup)+
      '<div class="rv-acc">'+
        (ch.unir_con?"":'<button type="button" class="rv-b si" data-acc="publicado"'+(e==="publicado"?" disabled":"")+'>Publicar</button>'+
        '<button type="button" class="rv-b no" data-acc="descartado"'+(e==="descartado"?" disabled":"")+'>Descartar</button>')+
        (revisado(c)&&!cambios[id]?'<button type="button" class="rv-b" data-acc="pendiente">Volver a sin revisar</button>':"")+
        (cambios[id]?'<button type="button" class="rv-b" data-acc="deshacer">Deshacer</button>':"")+
      '</div></article>';
  }

  function pintar(){
    var lista=casos.filter(enVista).filter(coincide);
    var sin=casos.filter(function(c){ return !revisado(c); }).length;
    $("conteo").textContent=lista.length+" caso(s) en esta vista · "+sin+" sin revisar en total";
    $("lista").innerHTML=lista.length?lista.map(tarjeta).join(""):'<p class="rv-vacio">No hay casos en esta vista.</p>';
    var n=Object.keys(cambios).length;
    $("barra").hidden=!n;
    $("barra-txt").textContent=n+(n===1?" cambio sin guardar":" cambios sin guardar");
  }

  function cambiar(id,k,v){
    cambios[id]=cambios[id]||{};
    cambios[id][k]=v;
  }

  function guardar(intento){
    intento=intento||1;
    var btn=$("guardar"); btn.disabled=true; btn.textContent="Guardando…";
    var hoy=new Date().toISOString().slice(0,10);
    return leerArchivo("data/casos.json").then(function(f){
      var r=aplicar(f.datos,JSON.parse(JSON.stringify(cambios)),usuario,hoy);
      var n=r.aplicados;
      var msg="Revisar "+n+(n===1?" caso":" casos")+" desde el panel";
      return gh(API+"data/casos.json",{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:msg,content:b64(aJson(r.casos)),sha:f.sha,branch:RAMA})}).then(function(){ return r; });
    }).then(function(r){
      cambios={};
      $("barra-txt").textContent="";
      return cargar().then(function(){
        $("conteo").textContent="Guardado: "+r.aplicados+" caso(s)"+(r.faltan.length?" ("+r.faltan.length+" ya no existían)":"")+". La página pública se actualiza en unos 2 minutos.";
      });
    }).catch(function(e){
      // 409: el scraper guardó algo mientras tanto; se vuelve a leer y aplicar.
      if((e.status===409||e.status===422)&&intento<3) return guardar(intento+1);
      alertar("No se pudo guardar: "+(e.message||e)+". Tus cambios siguen aquí; intenta de nuevo.");
    }).then(function(){ btn.disabled=false; btn.textContent="Guardar"; });
  }
  function alertar(t){ $("barra-txt").textContent=t; }

  document.addEventListener("DOMContentLoaded",function(){});
  var dl=document.createElement("datalist"); dl.id="dl-barrios"; document.body.appendChild(dl);
  var f=$("f-tipo"); TIPOS.forEach(function(t){ var o=document.createElement("option"); o.value=t; o.textContent=NOMBRE_TIPO[t]; f.appendChild(o); });

  $("entrar").addEventListener("click",function(){ var v=$("clave").value.trim(); if(v) entrar(v); });
  $("clave").addEventListener("keydown",function(e){ if(e.key==="Enter"){ var v=this.value.trim(); if(v) entrar(v); } });
  $("salir").addEventListener("click",function(){
    if(Object.keys(cambios).length&&!confirm("Tienes cambios sin guardar. ¿Salir de todos modos?")) return;
    guardarLS(null); clave=null; cambios={}; casos=[]; $("s-panel").hidden=true; $("s-login").hidden=false; $("barra").hidden=true; $("clave").value="";
  });
  $("vista").addEventListener("click",function(e){
    var b=e.target.closest("button"); if(!b) return;
    vista=b.dataset.v;
    [].forEach.call(this.querySelectorAll("button"),function(x){ x.setAttribute("aria-pressed",x===b?"true":"false"); });
    pintar();
  });
  $("buscar").addEventListener("input",pintar);
  $("f-tipo").addEventListener("change",pintar);
  $("lista").addEventListener("change",function(e){
    var el=e.target, k=el.dataset.k; if(!k) return;
    var id=el.closest(".rv-caso").dataset.id;
    cambiar(id,k,el.value.trim());
    pintar();
  });
  $("lista").addEventListener("focusin",function(e){
    if(e.target.dataset.k==="barrio"&&!dl.childElementCount) dl.innerHTML=barrios.map(function(b){ return '<option value="'+esc(b)+'">'; }).join("");
  });
  $("lista").addEventListener("click",function(e){
    var b=e.target.closest("button[data-acc]"); if(!b) return;
    var id=b.closest(".rv-caso").dataset.id, acc=b.dataset.acc;
    if(acc==="deshacer") delete cambios[id];
    else if(acc==="unir") cambios[id]={unir_con:b.dataset.con};
    else cambiar(id,"estado",acc);
    pintar();
  });
  $("descartar-cambios").addEventListener("click",function(){ cambios={}; pintar(); });
  $("guardar").addEventListener("click",function(){ guardar(); });
  window.addEventListener("beforeunload",function(e){ if(Object.keys(cambios).length){ e.preventDefault(); e.returnValue=""; } });

  var guardada=leerLS();
  if(guardada){ $("clave").value=guardada; entrar(guardada); }
})(typeof window!=="undefined"?window:globalThis);
