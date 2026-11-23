/* Utilidades compartidas: carga de datos con estados, formato, filtros en la URL y mapa. */
(function(){
  var O=window.OBAQ=window.OBAQ||{};
  var MESES=["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"];
  var MES3=["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"];
  O.MESES=MESES;O.MES3=MES3;
  O.TIPOS={hom:"Homicidio",les:"Lesiones",hur:"Hurto",ext:"Extorsión",otr:"Otros"};
  O.MUNICIPIOS=["Barranquilla","Soledad","Malambo","Galapa","Puerto Colombia"];
  O.$=function(id){return document.getElementById(id)};
  O.esc=O.esc||function(s){return String(s==null?"":s).replace(/[&<>"']/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]})};
  O.num=function(n){return n==null?"—":Number(n).toLocaleString("es-CO")};
  O.mes=function(m,corto){var p=m.split("-");return corto?MES3[+p[1]-1]+" "+p[0].slice(2):MESES[+p[1]-1]+" de "+p[0]};
  O.dia=function(iso){var d=new Date(iso+"T12:00:00");return d.getDate()+" de "+MESES[d.getMonth()]};
  O.fechaHora=function(iso){var d=new Date(iso);if(isNaN(d))return iso;
    return d.toLocaleString("es-CO",{timeZone:"America/Bogota",day:"numeric",month:"long",year:"numeric",hour:"numeric",minute:"2-digit"})};
  O.pct=function(a,b){return b?Math.round(100*(a-b)/b):null};
  O.signo=function(v){return v==null?"":(v>0?"+":"")+v+" %"};
  O.meses=function(desde,hasta){var out=[],a=+desde.slice(0,4),m=+desde.slice(5);var b=+hasta.slice(0,4),n=+hasta.slice(5);
    while(a<b||(a===b&&m<=n)){out.push(a+"-"+(m<10?"0":"")+m);m++;if(m>12){m=1;a++}}return out};

  // Carga con estados: el contenedor muestra "Cargando…" y, si falla, un error claro (nunca un 0).
  O.cargar=function(url){return fetch(url,{cache:"no-cache"}).then(function(r){if(!r.ok)throw new Error("HTTP "+r.status);return r.json()})};
  O.estado=function(el,tipo,texto){if(typeof el==="string")el=O.$(el);if(!el)return;
    el.innerHTML='<p class="estado '+tipo+'" role="'+(tipo==="error"?"alert":"status")+'">'+O.esc(texto)+"</p>"};

  // Filtros en la URL para compartir una vista.
  O.leerURL=function(def){var p=new URLSearchParams(location.search),o={};for(var k in def)o[k]=p.has(k)?p.get(k):def[k];return o};
  O.escribirURL=function(st,def){var p=new URLSearchParams();for(var k in st)if(st[k]!==def[k]&&st[k]!==""&&st[k]!=null)p.set(k,st[k]);
    var q=p.toString();history.replaceState(null,"",location.pathname+(q?"?"+q:"")+location.hash)};

  // Escala de color fija (no cambia con el filtro ni con el zoom).
  O.BINS=[[1,3,"1–2"],[3,6,"3–5"],[6,10,"6–9"],[10,20,"10–19"],[20,Infinity,"20 o más"]];
  O.bin=function(n){for(var i=0;i<O.BINS.length;i++)if(n<O.BINS[i][1])return i;return O.BINS.length-1};
  O.css=function(v){return getComputedStyle(document.documentElement).getPropertyValue(v).trim()};
  O.color=function(n){return O.css("--q"+(O.bin(n)+1))};
  O.etiqueta=function(n){return n<3?"<3":String(n)};

  // Mapa base y gestos: en celular un dedo desplaza la página y dos dedos mueven el mapa;
  // en computador la rueda solo hace zoom con Ctrl o ⌘.
  O.mapa=function(id,opc){
    opc=opc||{};
    var tactil=window.matchMedia&&window.matchMedia("(pointer:coarse)").matches;
    var map=L.map(id,{scrollWheelZoom:false,dragging:!tactil,tap:false,zoomSnap:0.5,minZoom:10,maxZoom:16,
      zoomControl:opc.zoom!==false,attributionControl:true}).setView([10.955,-74.8],opc.zoomInicial||12);
    var cont=map.getContainer();
    if(tactil)cont.style.touchAction="pan-y";
    var aviso=document.createElement("div");aviso.className="gesto";aviso.setAttribute("aria-hidden","true");
    aviso.textContent=tactil?"Usa dos dedos para mover el mapa":"Usa Ctrl + rueda (⌘ en Mac) para acercar";cont.appendChild(aviso);
    var tm;function mostrar(){aviso.classList.add("on");clearTimeout(tm);tm=setTimeout(function(){aviso.classList.remove("on")},1200)}
    cont.addEventListener("wheel",function(e){if(e.ctrlKey||e.metaKey){e.preventDefault();map.setZoom(map.getZoom()+(e.deltaY<0?0.5:-0.5))}else mostrar()},{passive:false});
    if(tactil)cont.addEventListener("touchstart",function(e){if(e.touches.length===1)mostrar()},{passive:true});
    map.createPane("etiquetas").style.zIndex=450;map.getPane("etiquetas").style.pointerEvents="none";
    var base=null,ref=null;
    function teselas(){
      if(base)map.removeLayer(base);if(ref)map.removeLayer(ref);
      // Mapa base gris de Esri (claro u oscuro) con nombres de calles encima. No pide clave.
      var tono=O.isDark()?"Dark":"Light",u="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_"+tono+"_Gray_";
      base=L.tileLayer(u+"Base/MapServer/tile/{z}/{y}/{x}",{maxZoom:16,attribution:'Mapa base &copy; <a href="https://www.esri.com/">Esri</a>, HERE, Garmin, &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'}).addTo(map);
      ref=L.tileLayer(u+"Reference/MapServer/tile/{z}/{y}/{x}",{maxZoom:16,pane:"etiquetas"}).addTo(map);
    }
    teselas();O.alCambiarTema(teselas);
    return map;
  };

  // Mapa de calor con radio en metros reales: se convierte a píxeles en cada zoom y la
  // intensidad máxima es fija, así el color significa lo mismo a cualquier escala.
  O.Calor=window.L&&L.Layer?L.Layer.extend({
    initialize:function(puntos,opc){this._p=puntos;this._o=L.extend({radio:300,max:8},opc)},
    setPuntos:function(p){this._p=p;this._dibujar();return this},
    onAdd:function(map){this._map=map;var c=this._c=L.DomUtil.create("canvas","leaflet-layer calor");
      c.style.pointerEvents="none";map.getPanes().overlayPane.appendChild(c);
      map.on("moveend zoomend resize",this._dibujar,this);map.on("zoomstart",this._ocultar,this);this._dibujar()},
    _ocultar:function(){this._c.style.visibility="hidden"},
    onRemove:function(map){L.DomUtil.remove(this._c);map.off("moveend zoomend resize",this._dibujar,this);map.off("zoomstart",this._ocultar,this)},
    radioPx:function(){var m=this._map,lat=m.getCenter().lat,z=m.getZoom();
      return this._o.radio/(40075016.686*Math.cos(lat*Math.PI/180)/Math.pow(2,z+8))},
    _paleta:function(){if(this._pal)return this._pal;var c=document.createElement("canvas");c.width=1;c.height=256;var g=c.getContext("2d"),gr=g.createLinearGradient(0,0,0,256);
      [[0,"rgba(255,244,199,0)"],[.15,"#FFF4C7"],[.35,"#FCD45E"],[.55,"#F2A033"],[.75,"#DE5B25"],[1,"#AD1F18"]].forEach(function(s){gr.addColorStop(s[0],s[1])});
      g.fillStyle=gr;g.fillRect(0,0,1,256);return this._pal=g.getImageData(0,0,1,256).data},
    _dibujar:function(){var m=this._map;if(!m)return;var t=m.getSize(),c=this._c,dpr=window.devicePixelRatio||1;c.style.visibility="visible";
      c.width=t.x*dpr;c.height=t.y*dpr;c.style.width=t.x+"px";c.style.height=t.y+"px";
      L.DomUtil.setPosition(c,m.containerPointToLayerPoint([0,0]));
      var g=c.getContext("2d"),r=Math.max(2,this.radioPx())*dpr,max=this._o.max;g.clearRect(0,0,c.width,c.height);
      // Núcleo gaussiano: el aporte de cada punto llega a cero a la distancia del radio.
      this._p.forEach(function(p){var pt=m.latLngToContainerPoint(p),x=pt.x*dpr,y=pt.y*dpr;if(x<-r||y<-r||x>c.width+r||y>c.height+r)return;
        var gr=g.createRadialGradient(x,y,0,x,y,r);gr.addColorStop(0,"rgba(0,0,0,"+Math.min(1,p[2]/max)+")");gr.addColorStop(1,"rgba(0,0,0,0)");
        g.globalCompositeOperation="lighter";g.fillStyle=gr;g.beginPath();g.arc(x,y,r,0,6.2832);g.fill()});
      var img=g.getImageData(0,0,c.width,c.height),d=img.data,pal=this._paleta();
      for(var i=3;i<d.length;i+=4){var a=d[i];if(!a)continue;var j=a*4;d[i-3]=pal[j];d[i-2]=pal[j+1];d[i-1]=pal[j+2];d[i]=Math.min(235,40+a)}
      g.putImageData(img,0,0)}
  }):null;

  // Gráfico de barras por mes en SVG, accesible. series: [{clave, nombre, color}], datos: [{mes, ...}]
  O.barrasMes=function(el,datos,series,opc){opc=opc||{};if(typeof el==="string")el=O.$(el);
    el._barras=[datos,series,opc]; // para volver a dibujarlo al ancho de la imagen compartida
    var W=Math.round(Math.min(760,Math.max(300,el.clientWidth||640))),H=opc.alto||(W<500?220:260),m={l:36,r:20,t:14,b:30};
    var max=1;datos.forEach(function(d){series.forEach(function(s){if(d[s.clave]>max)max=d[s.clave]})});
    var step=max>200?50:max>80?20:max>40?10:max>16?5:max>6?2:1,ymax=Math.ceil(max/step)*step,iw=W-m.l-m.r,ih=H-m.t-m.b,bw=iw/Math.max(1,datos.length),sw=bw*.78/series.length;
    var s='<svg viewBox="0 0 '+W+" "+H+'" role="img" aria-label="'+O.esc(opc.alt||"")+'"><defs><pattern id="trama-'+el.id+'" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" fill="var(--surface)"/><line x1="0" y1="0" x2="0" y2="6" stroke="var(--muted)" stroke-width="3"/></pattern></defs>';
    for(var y=0;y<=ymax;y+=step){var yy=m.t+ih-ih*y/ymax;s+='<line class="gl" x1="'+m.l+'" x2="'+(W-m.r)+'" y1="'+yy+'" y2="'+yy+'"/><text x="'+(m.l-6)+'" y="'+(yy+4)+'" text-anchor="end">'+y+"</text>"}
    var cada=Math.ceil(datos.length/(W<500?5:10));
    datos.forEach(function(d,i){var x0=m.l+i*bw+bw*.11;
      series.forEach(function(se,k){var v=d[se.clave];if(v==null)return;var h=ih*v/ymax,x=x0+k*sw,inc=d.incompleto&&d.incompleto.indexOf(se.clave)>=0;
        s+='<rect x="'+x.toFixed(1)+'" y="'+(m.t+ih-h).toFixed(1)+'" width="'+Math.max(1,sw-1).toFixed(1)+'" height="'+h.toFixed(1)+'" fill="'+(inc?"url(#trama-"+el.id+")":se.color)+'"'+(inc?' stroke="'+se.color+'" stroke-width="1.5"':"")+'><title>'+O.esc(se.nombre+", "+O.mes(d.mes)+": "+O.num(v)+(inc?" (incompleto)":""))+"</title></rect>"});
      if((datos.length-1-i)%cada===0)s+='<text x="'+(x0+bw*.39).toFixed(1)+'" y="'+(H-10)+'" text-anchor="middle">'+O.mes(d.mes,true)+"</text>"});
    el.innerHTML=s+"</svg>"};
  // Puntos aproximados: cada caso es un punto puesto al azar (con semilla fija) dentro de los
  // cuadros de su zona fusionada. Nunca usa la ubicación exacta; dos visitas ven lo mismo.
  O.DLAT=400/111320;O.DLON=400/(111320*Math.cos(10.97*Math.PI/180));
  function semilla(t){var h=2166136261;for(var i=0;i<t.length;i++){h^=t.charCodeAt(i);h=Math.imul(h,16777619)}
    return function(){h=h+0x6D2B79F5|0;var x=Math.imul(h^h>>>15,1|h);x=x+Math.imul(x^x>>>7,61|x)^x;return((x^x>>>14)>>>0)/4294967296}}
  // zonas: [{id, celdas}], casos: {idZona: [color, color, …]}
  O.puntos=function(capa,zonas,casos,opc){opc=opc||{};var r=L.canvas({padding:.3}),borde=O.isDark()?"rgba(0,0,0,.7)":"rgba(255,255,255,.9)";
    zonas.forEach(function(z){var cs=casos[z.id];if(!cs||!cs.length)return;var rnd=semilla(z.id),n=cs.length;
      var txt=opc.interactivo===false?null:(n<3?"Menos de 3 casos":O.num(n)+" casos")+" en esta zona.<br>Cada punto es un caso puesto al azar dentro de la zona, no el lugar del hecho.";
      cs.forEach(function(col){var c=z.celdas[Math.floor(rnd()*z.celdas.length)],la=(c[0]+.1+.8*rnd())*O.DLAT,lo=(c[1]+.1+.8*rnd())*O.DLON;
        var m=L.circleMarker([la,lo],{renderer:r,radius:opc.radio||4,fillColor:col,fillOpacity:.85,color:borde,weight:.8,interactive:!!txt});
        if(txt)m.bindTooltip(txt);m.addTo(capa)})})};

  // Clave de barrio para unir nombres de los datos con los límites. Igual que clave() en publico/nombres_barrio.py:
  // sin tildes ni signos, sin «barrio», «urbanización» ni «etapa», y números en cifras («Siete» → 7, «II» → 2).
  var NUM={uno:"1",primero:"1",dos:"2",tres:"3",cuatro:"4",cinco:"5",seis:"6",siete:"7",ocho:"8",nueve:"9",diez:"10",once:"11",doce:"12",trece:"13",catorce:"14",quince:"15",veinte:"20",
    i:"1",ii:"2",iii:"3",iv:"4",v:"5",vi:"6",vii:"7",viii:"8",ix:"9",x:"10"};
  O.claveBarrio=function(t){var k=String(t||"").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g,"").replace(/[^a-z0-9ñ]+/g," ").trim()
    .replace(/^(barrio|urbanizacion|urb|conjunto residencial|conjunto|ciudadela|sector|asentamiento)\s+/,"");
    return k.split(" ").filter(function(w){return w&&w!=="etapa"}).map(function(w){return NUM[w]||w}).join(" ")};
  // Misma clave sin artículo inicial («El Limón» → «limon»), para el segundo intento.
  O.sinArticulo=function(k){return k.replace(/^(el|la|los|las) /,"")};
})();
