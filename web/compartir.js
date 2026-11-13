/* Compartir gráficos como imagen (PNG) para redes sociales.
   Cada bloque con [data-compartir] recibe un botón. La imagen lleva el gráfico,
   el delito y el municipio elegidos, la fuente y la dirección del sitio. */
(function(){
  // Ícono de compartir al estilo iOS: flecha que sale de una caja abierta.
  var ICONO='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 2.8v11.4M8.3 6.4 12 2.8l3.7 3.6M8.6 9.6H7a2 2 0 0 0-2 2v7.6a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-7.6a2 2 0 0 0-2-2h-1.6"/></svg>';
  var lib=null,tactil=window.matchMedia&&window.matchMedia("(pointer:coarse)").matches;

  function cargar(){
    if(window.htmlToImage)return Promise.resolve(window.htmlToImage);
    if(lib)return lib;
    lib=new Promise(function(ok,mal){var s=document.createElement("script");s.src="html-to-image.js";s.onload=function(){ok(window.htmlToImage)};s.onerror=function(){lib=null;mal(new Error("no cargó la librería"))};document.head.appendChild(s)});
    return lib;
  }
  function sitio(){var p=location.pathname.replace(/[^/]*$/,"");return (location.host+p).replace(/\/$/,"")}
  function slug(t){return t.normalize("NFD").replace(/[̀-ͯ]/g,"").toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"").slice(0,90).replace(/-[^-]*$/,"")}

  function armar(bloque){
    var C=window.OBAQ&&OBAQ.captura,caja=document.createElement("div");caja.className="captura";
    var logo=document.querySelector(".logo svg");
    caja.innerHTML='<div class="cap-top"><span class="cap-marca">'+(logo?logo.outerHTML:"")+'Observatorio <b>BAQ</b></span><span class="cap-ctx"></span></div><div class="cap-flag"></div>';
    if(C)caja.querySelector(".cap-ctx").textContent=C.contexto();
    var copia=bloque.cloneNode(true);
    var svg=copia.querySelector("#serie");if(svg&&C&&C.serie)svg.innerHTML=C.serie(984);
    [].forEach.call(copia.querySelectorAll(".comp,.como"),function(e){e.remove()});
    [].forEach.call(copia.querySelectorAll("[id]"),function(e){e.removeAttribute("id")});
    copia.removeAttribute("data-compartir");copia.style.margin="0";
    caja.appendChild(copia);
    var pie=document.createElement("div");pie.className="cap-pie";
    pie.innerHTML="<span></span><b></b>";pie.firstChild.textContent=(C?C.fuente+" ":"")+"Cifras provisionales.";pie.lastChild.textContent=sitio();
    caja.appendChild(pie);
    document.body.appendChild(caja);
    var ancho=1080;[].forEach.call(caja.querySelectorAll(".tablewrap"),function(t){ancho=Math.max(ancho,t.scrollWidth+96)});
    caja.style.width=Math.min(ancho,2400)+"px";
    return caja;
  }

  function entregar(blob,nombre,titulo){
    var file=null;try{file=new File([blob],nombre,{type:"image/png"})}catch(e){}
    if(tactil&&file&&navigator.canShare&&navigator.canShare({files:[file]}))
      return navigator.share({files:[file],title:titulo,text:titulo+" · "+location.href}).catch(function(e){if(e&&e.name!=="AbortError")bajar(blob,nombre)});
    bajar(blob,nombre);
  }
  function bajar(blob,nombre){var u=URL.createObjectURL(blob),a=document.createElement("a");a.href=u;a.download=nombre;document.body.appendChild(a);a.click();a.remove();setTimeout(function(){URL.revokeObjectURL(u)},4000)}

  function compartir(bloque,btn){
    var h=bloque.querySelector("h2"),titulo=h?h.textContent.trim():"Gráfico",C=window.OBAQ&&OBAQ.captura;
    var nombre="observatorio-baq-"+slug(titulo+(C?"-"+C.contexto():""))+".png";
    btn.disabled=true;btn.setAttribute("aria-busy","true");
    var caja=null;
    cargar().then(function(H){
      caja=armar(bloque);
      var bg=getComputedStyle(caja).backgroundColor,opc={pixelRatio:2,backgroundColor:bg,style:{position:"static",left:"0",top:"0"}};
      return H.toBlob(caja,opc).catch(function(){opc.skipFonts=true;return H.toBlob(caja,opc)});
    }).then(function(blob){if(!blob)throw new Error("imagen vacía");return entregar(blob,nombre,titulo)})
    .catch(function(e){aviso("No se pudo crear la imagen ("+e.message+").")})
    .then(function(){if(caja)caja.remove();btn.disabled=false;btn.removeAttribute("aria-busy")});
  }
  function aviso(m){var p=document.createElement("div");p.className="comp-aviso";p.setAttribute("role","status");p.textContent=m;document.body.appendChild(p);setTimeout(function(){p.remove()},5000)}

  [].forEach.call(document.querySelectorAll("[data-compartir]"),function(b){
    var btn=document.createElement("button");btn.type="button";btn.className="comp";
    var et=tactil?"Compartir este gráfico como imagen":"Descargar este gráfico como imagen";
    btn.innerHTML=ICONO;btn.title=et;btn.setAttribute("aria-label",et);
    btn.onclick=function(){compartir(b,btn)};
    b.classList.add("con-comp");b.insertBefore(btn,b.firstChild);
  });
})();
