/* Estadísticas oficiales: Policía Nacional (SIEDCO), área metropolitana de Barranquilla. */
(function(){
  var $=function(id){return document.getElementById(id)},esc=OBAQ.esc;
  var NOM={todos:"Todos los delitos",homicidio:"Homicidio intencional",lesiones:"Lesiones personales",hurto:"Hurtos (todos)",hurto_personas:"Hurto a personas",hurto_motos:"Hurto de motos",hurto_carros:"Hurto de carros",hurto_comercio:"Hurto a comercio",hurto_residencias:"Hurto a residencias",hurto_entidades:"Hurto a entidades financieras",extorsion:"Extorsión",violencia_intrafamiliar:"Violencia intrafamiliar",violencia_sexual:"Delitos sexuales",amenazas:"Amenazas",secuestro:"Secuestro",transito:"Tránsito (muertes y lesiones)",otros:"Otros"};
  var MES=["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"];
  var MESL=["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"];
  var DIAS=["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"];
  var D,U,st={muni:"",cat:"homicidio"};
  var nf=function(n){return Math.round(n).toLocaleString("es-CO")};
  var pct=function(a,b){return b?Math.round(100*(a-b)/b):null};
  var varHtml=function(v){return v===null?"—":'<span class="'+(v>0?"up":"dn")+'">'+(v>0?"+":"")+v+" %</span>"};
  var css=function(v){return getComputedStyle(document.documentElement).getPropertyValue(v).trim()};

  function okCat(c){return st.cat==="todos"||c===st.cat||(st.cat==="hurto"&&c.indexOf("hurto")===0)}
  var CATS=[];
  // ¿La Policía publicó datos de esta categoría (o de todas las de la selección) ese año?
  function cubreCat(c,a){var l=D.cobertura&&D.cobertura[c];return !l||l.indexOf(a)>=0}
  function cubre(a){return CATS.every(function(c){return !okCat(c)||cubreCat(c,a)})}
  function okMuni(m){return !st.muni||m===st.muni}
  function tabla(n){return D.tablas[n].filas}
  // Serie mensual de la selección: {clave año*12+mes-1: n}
  function serie(){var s={};tabla("mensual").forEach(function(r){if(okMuni(r[2])&&okCat(r[3])){var k=r[0]*12+r[1]-1;s[k]=(s[k]||0)+r[4]}});
    var g=rango();for(var k=g[0];k<=g[1];k++)if(!cubre(Math.floor(k/12)))s[k]=null;return s}
  // Rango de toda la base, y rango de la selección: empieza en el primer año con datos de
  // todos sus delitos (antes de 2020 faltan archivos de algunos, así que "Todos" empieza en 2020).
  var R0;
  function rangoGlobal(){if(R0==null){var ks=tabla("mensual").map(function(r){return r[0]*12+r[1]-1});R0=Math.min.apply(null,ks)}return [R0,U.anio*12+U.mes-1]}
  function rango(){var g=rangoGlobal();for(var a=Math.floor(g[0]/12);a<U.anio;a++)if(cubre(a))break;return [Math.max(g[0],a*12),g[1]]}
  function nomSel(){return NOM[st.cat]}
  function etiqueta(k){return MES[k%12]+" "+Math.floor(k/12)}

  function kpis(s){
    var r=rango(),fin=r[1],sum=function(a,b){var t=0;for(var k=a;k<=b;k++)t+=s[k]||0;return t};
    var u12=sum(fin-11,fin),p12=sum(fin-23,fin-12),A=U.anio,M=U.mes;
    var ytd=sum(A*12,fin),pytd=sum((A-1)*12,(A-1)*12+M-1);
    var max=-1,km=0;for(var k=r[0];k<=fin;k++)if((s[k]||0)>max){max=s[k]||0;km=k}
    $("kpis").innerHTML=[
      ["Últimos 12 meses",nf(u12),varHtml(pct(u12,p12))+" frente a los 12 anteriores"],
      ["En "+A+" (ene–"+MES[M-1]+")",nf(ytd),varHtml(pct(ytd,pytd))+" frente a "+(A-1)],
      ["Promedio mensual",nf(u12/12),"en los últimos 12 meses"],
      ["Mes con más casos",nf(max),etiqueta(km)+" (desde "+Math.floor(r[0]/12)+")"]
    ].map(function(x){return '<div class="kpi"><p class="k">'+x[0]+"</p><b>"+x[1]+"</b><small>"+x[2]+"</small></div>"}).join("");
  }

  function grafSerie(s){
    var r=rango(),n=r[1]-r[0]+1,W=960,H=320,m={l:44,r:12,t:16,b:30},iw=W-m.l-m.r,ih=H-m.t-m.b,bw=iw/n;
    var vals=[],ma=[];for(var i=0;i<n;i++){var v0=s[r[0]+i];vals.push(v0===null?null:v0||0)}
    for(i=0;i<n;i++){if(i<11){ma.push(null);continue}var t=0,ok=true;for(var j=i-11;j<=i;j++){if(vals[j]===null)ok=false;t+=vals[j]||0}ma.push(ok?t/12:null)}
    var mx=Math.max.apply(null,vals.map(function(v){return v||0}).concat([1])),raw=mx/5,mag=Math.pow(10,Math.floor(Math.log10(raw||1))),step=[1,2,5,10].map(function(f){return f*mag}).filter(function(v){return v>=raw})[0]||1;step=Math.max(1,step);
    var ymax=Math.ceil(mx/step)*step,Y=function(v){return m.t+ih-ih*v/ymax};
    var o='<svg viewBox="0 0 '+W+" "+H+'" role="img" aria-label="Serie mensual con media móvil de 12 meses">';
    for(var y=0;y<=ymax;y+=step)o+='<line class="gl" x1="'+m.l+'" x2="'+(W-m.r)+'" y1="'+Y(y)+'" y2="'+Y(y)+'"/><text x="'+(m.l-6)+'" y="'+(Y(y)+4)+'" text-anchor="end">'+nf(y)+"</text>";
    for(i=0;i<n;i++){var k=r[0]+i,x=m.l+i*bw;
      if(vals[i]===null){o+='<rect x="'+x.toFixed(1)+'" y="'+m.t+'" width="'+bw.toFixed(1)+'" height="'+ih+'" fill="var(--band)"><title>'+etiqueta(k)+': sin datos publicados</title></rect>';if(k%12===0)o+='<text x="'+(x+2).toFixed(1)+'" y="'+(H-10)+'">'+Math.floor(k/12)+"</text>";continue}
      o+='<rect x="'+(x+bw*.12).toFixed(1)+'" y="'+Y(vals[i]).toFixed(1)+'" width="'+(bw*.76).toFixed(1)+'" height="'+(m.t+ih-Y(vals[i])).toFixed(1)+'" fill="var(--qna)"><title>'+etiqueta(k)+": "+nf(vals[i])+(ma[i]!==null?" · media 12 meses: "+nf(ma[i]):"")+"</title></rect>";
      if(k%12===0)o+='<text x="'+(x+2).toFixed(1)+'" y="'+(H-10)+'">'+Math.floor(k/12)+"</text>"}
    var tramos=[[]];ma.forEach(function(v,i){if(v===null){if(tramos[tramos.length-1].length)tramos.push([]);return}tramos[tramos.length-1].push((m.l+i*bw+bw/2).toFixed(1)+","+Y(v).toFixed(1))});
    tramos.forEach(function(pts){if(pts.length>1)o+='<polyline points="'+pts.join(" ")+'" fill="none" stroke="var(--hot)" stroke-width="2.5" stroke-linejoin="round"/>'});
    $("serie").innerHTML=o+"</svg>";
    var last=ma[n-1],prev=ma[n-13];
    var huecos=[];for(var a=Math.floor(r[0]/12);a<=U.anio;a++)if(!cubre(a))huecos.push(a);
    var g0=Math.floor(rangoGlobal()[0]/12),a0=Math.floor(r[0]/12),ini="";
    if(a0>g0)ini=(st.cat==="todos"||st.cat==="hurto"?"Esta suma empieza en "+a0+" porque antes faltan los archivos de algunos delitos; elige un delito para ver su historia desde "+g0+". ":"La serie empieza en "+a0+", el primer año con archivo publicado. ");
    $("serie-nota").innerHTML=ini+(huecos.length?"La Policía no publicó el archivo de "+(huecos.length>1?"los años "+huecos.slice(0,-1).join(", ")+" y "+huecos[huecos.length-1]:huecos[0])+" para este delito; esos meses aparecen en gris y no entran en los promedios. ":"")+"La media móvil promedia los 12 meses anteriores a cada punto, así que no la afectan las temporadas. Hoy está en <b>"+(last!==null?nf(last):"—")+"</b> casos por mes"+(prev!=null?", "+varHtml(pct(last,prev))+" frente a hace un año.":".");
  }

  function escala(vals){var v=vals.filter(function(x){return x>0}).sort(function(a,b){return a-b});
    var q=[.2,.4,.6,.8].map(function(p){return v.length?v[Math.min(v.length-1,Math.floor(p*v.length))]:0});
    return function(x){if(!x)return -1;for(var i=0;i<4;i++)if(x<=q[i])return i;return 4}}
  function celda(x,b,txt){if(b<0)return '<td class="v">'+(txt==null?"":txt)+"</td>";var dark=OBAQ.isDark(),fg=dark?(b>=3?"#111":"#eee"):(b>=3?"#fff":"#13201A");
    return '<td style="background:var(--q'+(b+1)+');color:'+fg+'" title="'+esc(txt)+'">'+txt+"</td>"}
  function leyenda(id,nota){$(id).innerHTML="<span>Menos</span>"+[1,2,3,4,5].map(function(i){return '<i style="background:var(--q'+i+')"></i>'}).join("")+"<span>Más</span>"+(nota?"<span>· "+nota+"</span>":"")}

  function calorAnioMes(s){
    var r=rango(),a0=Math.floor(r[0]/12),vals=[];for(var k=r[0];k<=r[1];k++)vals.push(s[k]||0);
    var b=escala(vals),o='<table class="heat"><thead><tr><th></th>'+MES.map(function(x){return "<th>"+x+"</th>"}).join("")+'<th class="r">Total</th></tr></thead><tbody>';
    for(var a=a0;a<=U.anio;a++){var tot=0,hay=cubre(a);o+='<tr><th class="r">'+a+"</th>";
      for(var mm=0;mm<12;mm++){var k=a*12+mm;if(k>r[1]){o+='<td class="v"></td>';continue}if(!hay){o+='<td class="v" title="Sin datos publicados">s. d.</td>';continue}var x=s[k]||0;tot+=x;o+=celda(x,b(x),nf(x))}
      o+='<td class="v"><b>'+(hay?nf(tot):"—")+"</b></td></tr>"}
    $("calor1").innerHTML=o+"</tbody></table>";leyenda("calor1-ley","colores por quintiles de todos los meses");
  }

  function calorDias(){
    var c={},tot={};tabla("dias").forEach(function(r){if(okMuni(r[2])&&okCat(r[3])&&cubre(r[0])){var k=r[0]+"-"+r[4];c[k]=(c[k]||0)+r[5];tot[r[0]]=(tot[r[0]]||0)+r[5]}});
    var anios=Object.keys(tot).map(Number).sort(),vals=[];
    anios.forEach(function(a){for(var d=0;d<7;d++)vals.push(tot[a]?(c[a+"-"+d]||0)/tot[a]:0)});
    var b=escala(vals),o='<table class="heat"><thead><tr><th></th>'+anios.map(function(a){return "<th>"+a+"</th>"}).join("")+"</tr></thead><tbody>";
    for(var d=0;d<7;d++){o+='<tr><th class="r">'+DIAS[d]+"</th>";anios.forEach(function(a){var p=tot[a]?(c[a+"-"+d]||0)/tot[a]:0;o+=celda(p,b(p),Math.round(100*p)+" %")});o+="</tr>"}
    $("calor2").innerHTML=o+"</tbody></table>";leyenda("calor2-ley","% de los casos de cada año; un reparto parejo sería 14 %");
  }

  function variacion(){
    var A=U.anio,M=U.mes,c={},anios={};
    tabla("mensual").forEach(function(r){if(okMuni(r[2])&&r[1]<=M){var k=r[3]+"|"+r[0];c[k]=(c[k]||0)+r[4];anios[r[0]]=1}});
    anios=Object.keys(anios).map(Number).sort();
    var cats=Object.keys(NOM).filter(function(x){return x!=="todos"&&x!=="hurto"&&anios.some(function(a){return c[x+"|"+a]})});
    cats.sort(function(x,y){return (c[y+"|"+A]||0)-(c[x+"|"+A]||0)});
    var o='<table class="tabla"><thead><tr><th>Delito</th>'+anios.map(function(a){return '<th class="n">'+a+"</th>"}).join("")+'<th class="n">'+A+" vs "+(A-1)+"</th></tr></thead><tbody>";
    cats.forEach(function(x){var fila=anios.map(function(a){return c[x+"|"+a]||0}),mx=Math.max.apply(null,fila.concat([1]));
      o+="<tr"+(x===st.cat?' style="background:var(--band)"':"")+"><td>"+NOM[x]+"</td>"+fila.map(function(v,j){if(!cubreCat(x,anios[j]))return '<td class="n" title="Sin datos publicados">—</td>';var i=Math.min(4,Math.floor(5*v/mx-1e-9));return '<td class="n" style="box-shadow:inset 0 -3px 0 var(--q'+(i+1)+')">'+nf(v)+"</td>"}).join("")+'<td class="n">'+varHtml(pct(c[x+"|"+A]||0,c[x+"|"+(A-1)]||0))+"</td></tr>"});
    $("variacion").innerHTML=o+"</tbody></table>";
    $("variacion-sub").textContent="Casos de enero a "+MESL[M-1]+" de cada año, para comparar periodos iguales"+(st.muni?" en "+st.muni:" en el área metropolitana")+". La raya de color marca el año más alto de cada fila.";
  }

  function municipios(){
    var r=rango(),fin=r[1],c={},p={},tot=0;
    tabla("mensual").forEach(function(x){if(!okCat(x[3]))return;var k=x[0]*12+x[1]-1;if(k>fin-12&&k<=fin){c[x[2]]=(c[x[2]]||0)+x[4];tot+=x[4]}else if(k>fin-24&&k<=fin-12)p[x[2]]=(p[x[2]]||0)+x[4]});
    var ms=Object.keys(c).sort(function(a,b){return c[b]-c[a]});
    $("munis").innerHTML='<table class="tabla"><thead><tr><th>Municipio</th><th class="n">Últimos 12 meses</th><th class="n">12 meses anteriores</th><th class="n">Variación</th><th class="n">% del área</th></tr></thead><tbody>'+
      ms.map(function(m){return "<tr"+(m===st.muni?' style="background:var(--band)"':"")+"><td>"+m+'</td><td class="n">'+nf(c[m])+'</td><td class="n">'+nf(p[m]||0)+'</td><td class="n">'+varHtml(pct(c[m],p[m]||0))+'</td><td class="n">'+Math.round(100*c[m]/tot)+" %</td></tr>"}).join("")+"</tbody></table>";
  }

  // Periodos de gobierno. Mes inicial y final (inclusive), en años y meses.
  // La Presidencia cambia el 7 de agosto: ese mes se cuenta para el gobierno que entra.
  var PERIODOS={
    presidente:{nombre:"Presidencia de la República",lista:[["Álvaro Uribe (2006–2010)",2006,8,2010,7],["Juan Manuel Santos I (2010–2014)",2010,8,2014,7],["Juan Manuel Santos II (2014–2018)",2014,8,2018,7],["Iván Duque (2018–2022)",2018,8,2022,7],["Gustavo Petro (2022–2026)",2022,8,2026,7],["Abelardo de la Espriella (2026–2030)",2026,8,2030,7]],
      nota:"El cambio de gobierno es el 7 de agosto; ese mes se cuenta completo para el gobierno que entra."},
    alcalde:{nombre:"Alcaldía de Barranquilla",lista:[["Alejandro Char (2008–2011)",2008,1,2011,12],["Elsa Noguera (2012–2015)",2012,1,2015,12],["Alejandro Char (2016–2019)",2016,1,2019,12],["Jaime Pumarejo (2020–2023)",2020,1,2023,12],["Alejandro Char (2024–2027)",2024,1,2027,12]],
      nota:"La Alcaldía responde por Barranquilla; para los demás municipios, elige uno en el filtro y compara con cautela."},
    gobernador:{nombre:"Gobernación del Atlántico",lista:[["Eduardo Verano (2008–2011)",2008,1,2011,12],["José Antonio Segebre (2012–2015)",2012,1,2015,12],["Eduardo Verano (2016–2019)",2016,1,2019,12],["Elsa Noguera (2020–2023)",2020,1,2023,12],["Eduardo Verano (2024–2027)",2024,1,2027,12]],nota:""}
  };
  var per="presidente";
  function gobiernos(s){
    var r=rango(),P=PERIODOS[per],filas=[];
    P.lista.forEach(function(g){var a=g[1]*12+g[2]-1,b=g[3]*12+g[4]-1,i0=Math.max(a,r[0]),i1=Math.min(b,r[1]);if(i1<i0)return;
      var t=0,nm=0;for(var k=i0;k<=i1;k++)if(s[k]!==null){t+=s[k]||0;nm++}if(!nm)return;filas.push({n:g[0],meses:nm,total:b-a+1,prom:t/nm,suma:t,desde:i0,hasta:i1})});
    var mx=Math.max.apply(null,filas.map(function(f){return f.prom}).concat([1]));
    var o=filas.map(function(f){return '<div class="hrow"><span class="lab">'+esc(f.n)+'</span><div class="track"><div class="fill" style="width:'+(100*f.prom/mx).toFixed(1)+'%;background:var(--'+(f.meses<f.total?"qna);color:var(--ink":"primary")+')">'+nf(f.prom)+"</div></div></div>"}).join("");
    $("gob-graf").innerHTML='<div class="gob">'+o+"</div>";
    $("gob-tabla").innerHTML='<table class="tabla"><thead><tr><th>Periodo</th><th class="n">Meses con datos</th><th class="n">Casos</th><th class="n">Promedio mensual</th><th class="n">Frente al periodo anterior</th></tr></thead><tbody>'+
      filas.map(function(f,i){var parcial=f.meses<f.total;return "<tr"+(parcial?' class="parcial"':"")+"><td>"+esc(f.n)+(parcial?" · "+etiqueta(f.desde)+" a "+etiqueta(f.hasta):"")+'</td><td class="n">'+f.meses+" de "+f.total+'</td><td class="n">'+nf(f.suma)+'</td><td class="n"><b>'+nf(f.prom)+'</b></td><td class="n">'+(i?varHtml(pct(f.prom,filas[i-1].prom)):"—")+"</td></tr>"}).join("")+"</tbody></table>";
    $("gob-sub").textContent=nomSel()+" en "+(st.muni||"el área metropolitana")+", promedio de casos por mes en cada periodo de la "+P.nombre+". Las barras grises son periodos con datos incompletos.";
    $("gob-nota").textContent=(P.nota?P.nota+" ":"")+"El promedio mensual permite comparar periodos de distinta duración, pero no mide por sí solo el efecto de un gobierno: también cambian la población, la denuncia (por ejemplo, la denuncia virtual) y la forma de registrar.";
  }

  function areaReparto(){
    var c={},tot={},glob={};
    tabla("mensual").forEach(function(r){if(!okCat(r[3])||!cubre(r[0]))return;var k=r[0]+"|"+r[2];c[k]=(c[k]||0)+r[4];tot[r[0]]=(tot[r[0]]||0)+r[4];glob[r[2]]=(glob[r[2]]||0)+r[4]});
    var ms=Object.keys(glob).sort(function(a,b){return glob[b]-glob[a]}),ys=Object.keys(tot).map(Number).sort();
    var COL={"Barranquilla":"--primary","Soledad":"--c-hur","Malambo":"--c-les","Galapa":"--c-ext","Puerto Colombia":"--c-otr"};
    $("area-titulo").textContent="¿Cuánto pesa Barranquilla en "+nomSel().toLowerCase()+"?";
    $("area-anios").innerHTML=ys.map(function(a){return '<div class="srow"><span>'+a+(a===U.anio?"*":"")+'</span><div class="stack">'+ms.map(function(m){var v=c[a+"|"+m]||0,w=100*v/tot[a];return w>0?'<span style="width:'+w.toFixed(2)+"%;background:var("+(COL[m]||"--qna")+')" title="'+esc(m)+": "+nf(v)+" ("+Math.round(w)+' %)">'+(w>=9?Math.round(w)+" %":"")+"</span>":""}).join("")+"</div></div>"}).join("")+
      '<div class="keyrow">'+ms.map(function(m){return '<span><i style="background:var('+(COL[m]||"--qna")+')"></i>'+esc(m)+"</span>"}).join("")+"</div>"+(tot[U.anio]?'<p class="note">* '+U.anio+" va de enero a "+MESL[U.mes-1]+".</p>":"");
    // Parte de Barranquilla por delito: primer año completo frente a los últimos 12 meses
    var r=rangoGlobal(),fin=r[1],a0=Math.floor(r[0]/12),cb={},ct={},pb={},pt={};
    tabla("mensual").forEach(function(x){var k=x[0]*12+x[1]-1,cat=x[3],b=x[2]==="Barranquilla";
      if(k>fin-12){ct[cat]=(ct[cat]||0)+x[4];if(b)cb[cat]=(cb[cat]||0)+x[4]}
      if(x[0]===a0&&cubreCat(cat,a0)){pt[cat]=(pt[cat]||0)+x[4];if(b)pb[cat]=(pb[cat]||0)+x[4]}});
    var cats=Object.keys(NOM).filter(function(x){return x!=="todos"&&x!=="hurto"&&ct[x]}).sort(function(x,y){return ct[y]-ct[x]});
    var sb=0,stt=0;cats.forEach(function(x){sb+=cb[x]||0;stt+=ct[x]});
    var barra=function(p){return '<div class="pbar"><i style="width:'+p.toFixed(1)+'%"></i><span>'+Math.round(p)+" %</span></div>"};
    $("area-delitos").innerHTML='<table class="tabla"><thead><tr><th>Delito</th><th class="n">Barranquilla</th><th class="n">Resto del área</th><th>% en Barranquilla (últimos 12 meses)</th><th class="n">En '+a0+"</th></tr></thead><tbody>"+
      cats.map(function(x){var b=cb[x]||0,p=100*b/ct[x],p0=pt[x]?100*(pb[x]||0)/pt[x]:null;return "<tr"+(x===st.cat||(st.cat==="hurto"&&x.indexOf("hurto")===0)?' style="background:var(--band)"':"")+"><td>"+NOM[x]+'</td><td class="n">'+nf(b)+'</td><td class="n">'+nf(ct[x]-b)+"</td><td>"+barra(p)+'</td><td class="n">'+(p0===null?"—":Math.round(p0)+" %")+"</td></tr>"}).join("")+
      '<tr><td><b>Todos</b></td><td class="n"><b>'+nf(sb)+'</b></td><td class="n"><b>'+nf(stt-sb)+"</b></td><td>"+barra(stt?100*sb/stt:0)+'</td><td class="n"></td></tr></tbody></table>';
    $("area-sub").textContent="Casos de los últimos 12 meses (a "+MESL[U.mes-1]+" de "+U.anio+") y la parte de Barranquilla en "+a0+" para ver si cambió.";
  }

  var PAL=["--c-hom","--c-hur","--c-les","--c-ext","--c-otr","--qna"];
  function apilado(tab,col,id,anios){
    var c={},tot={},glob={};
    tabla(tab).forEach(function(r){if(okMuni(r[1])&&okCat(r[2])&&cubre(r[0])){var k=r[0]+"|"+r[col];c[k]=(c[k]||0)+r[4];tot[r[0]]=(tot[r[0]]||0)+r[4];glob[r[col]]=(glob[r[col]]||0)+r[4]}});
    var top=Object.keys(glob).sort(function(a,b){return glob[b]-glob[a]}).slice(0,5),ys=Object.keys(tot).map(Number).sort();if(anios)ys=ys.slice(-anios);
    var lab=function(x){x=String(x);return x.charAt(0)+x.slice(1).toLowerCase()};
    var o=ys.map(function(a){var resto=tot[a];return '<div class="srow"><span>'+a+'</span><div class="stack">'+top.map(function(t,i){var v=c[a+"|"+t]||0;resto-=v;var w=100*v/tot[a];return w>0?'<span style="width:'+w.toFixed(2)+"%;background:var("+PAL[i]+')" title="'+esc(lab(t))+": "+nf(v)+'">'+(w>=9?Math.round(w)+" %":"")+"</span>":""}).join("")+(resto>0?'<span style="width:'+(100*resto/tot[a]).toFixed(2)+'%;background:var(--qna)" title="Otros: '+nf(resto)+'"></span>':"")+"</div></div>"}).join("");
    $(id).innerHTML=o+'<div class="keyrow">'+top.map(function(t,i){return '<span><i style="background:var('+PAL[i]+')"></i>'+esc(lab(t))+"</span>"}).join("")+(top.length?'<span><i style="background:var(--qna)"></i>Otros</span>':"")+"</div>";
  }

  function csv(){
    var s=serie(),r=rango(),filas=[["anio","mes","municipio","delito","casos","media_movil_12m"]],v=[];
    for(var k=r[0];k<=r[1];k++){var x=s[k]===null?null:s[k]||0;v.push(x);var u=v.slice(-12),ma=u.length===12&&u.indexOf(null)<0?u.reduce(function(a,b){return a+b},0)/12:"";
      filas.push([Math.floor(k/12),k%12+1,st.muni||"Área metropolitana",nomSel(),x===null?"":x,ma===""?"":ma.toFixed(1)])}
    var blob=new Blob(["﻿"+filas.map(function(f){return f.map(function(x){return /[",]/.test(x)?'"'+String(x).replace(/"/g,'""')+'"':x}).join(",")}).join("\n")],{type:"text/csv;charset=utf-8"});
    var a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download="observatorio-baq_"+st.cat+"_"+(st.muni||"area").toLowerCase().replace(/\s+/g,"-")+".csv";document.body.appendChild(a);a.click();setTimeout(function(){URL.revokeObjectURL(a.href);a.remove()},500);
  }

  function render(){
    var s=serie(),lugar=st.muni||"el área metropolitana";
    $("titulo-sel").textContent=nomSel()+" en "+lugar;
    kpis(s);grafSerie(s);calorAnioMes(s);calorDias();variacion();gobiernos(s);areaReparto();municipios();
    apilado("armas",3,"armas");apilado("genero",3,"genero",3);apilado("edad",3,"edad",3);
    try{history.replaceState(null,"","#"+st.cat+(st.muni?"/"+encodeURIComponent(st.muni):""))}catch(e){}
  }

  fetch("data/oficiales.json",{cache:"no-cache"}).then(function(r){if(!r.ok)throw new Error(r.status);return r.json()}).then(function(d){
    D=d;U=d.ultimo_mes;
    var ms={},cs={};tabla("mensual").forEach(function(r){ms[r[2]]=1;cs[r[3]]=1});CATS=Object.keys(cs);
    $("f-muni").innerHTML='<option value="">Área metropolitana</option>'+Object.keys(ms).sort().map(function(m){return '<option value="'+esc(m)+'">'+esc(m)+"</option>"}).join("");
    var orden=["todos","homicidio","hurto"].concat(Object.keys(NOM).filter(function(k){return cs[k]&&k!=="homicidio"}));
    $("f-cat").innerHTML=orden.map(function(k){return '<option value="'+k+'">'+NOM[k]+"</option>"}).join("");
    var h=decodeURIComponent(location.hash.slice(1)).split("/");if(NOM[h[0]])st.cat=h[0];if(h[1]&&ms[h[1]])st.muni=h[1];
    $("f-cat").value=st.cat;$("f-muni").value=st.muni;
    $("f-cat").onchange=function(e){st.cat=e.target.value;render()};
    $("f-muni").onchange=function(e){st.muni=e.target.value;render()};
    $("descargar").onclick=csv;
    [].forEach.call(document.querySelectorAll("[data-per]"),function(b){b.onclick=function(){per=b.dataset.per;[].forEach.call(document.querySelectorAll("[data-per]"),function(x){x.setAttribute("aria-pressed",x===b)});gobiernos(serie())}});
    $("desde").textContent="desde "+Math.floor(rangoGlobal()[0]/12);
    $("fuente").innerHTML="Fuente: Policía Nacional (SIEDCO). Datos de enero de "+Math.floor(rangoGlobal()[0]/12)+" a "+MESL[U.mes-1]+" de "+U.anio+", actualizados el "+esc(d.actualizado)+"."+(d.inicio_registro&&Math.floor(rangoGlobal()[0]/12)<d.inicio_registro?" Hasta "+(d.inicio_registro-1)+" vienen de los archivos por delito de alto impacto; desde "+d.inicio_registro+", del archivo con todos los delitos.":"")+" "+esc(d.nota.split(" dia_semana")[0])+' <a href="metodologia.html#policia">Cómo se procesan</a>.';
    OBAQ.alCambiarTema(render);
    render();
  }).catch(function(e){$("titulo-sel").textContent="No se pudieron cargar los datos ("+e.message+")."});
})();
