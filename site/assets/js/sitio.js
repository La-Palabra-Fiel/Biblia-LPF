/* La Palabra Fiel — comportamiento del sitio.
   Sin dependencias. Todo degrada con gracia si JS está desactivado. */
(function () {
  'use strict';

  var raiz = document.documentElement;

  function guardar(clave, valor) {
    try { localStorage.setItem(clave, valor); } catch (e) {}
  }

  /* ---- Tema claro / oscuro ---------------------------------------------- */
  document.addEventListener('click', function (ev) {
    var btn = ev.target.closest('[data-accion="tema"]');
    if (!btn) return;
    var nuevo = raiz.getAttribute('data-tema') === 'oscuro' ? 'claro' : 'oscuro';
    raiz.setAttribute('data-tema', nuevo);
    guardar('lbf-tema', nuevo);
  });

  /* ---- Controles del lector --------------------------------------------- */
  var ESCALAS = [0.88, 1, 1.14, 1.3, 1.5];

  function escalaActual() {
    var v = parseFloat(getComputedStyle(raiz).getPropertyValue('--escala-lectura')) || 1;
    var mejor = 1, dist = Infinity;
    ESCALAS.forEach(function (e) {
      var d = Math.abs(e - v);
      if (d < dist) { dist = d; mejor = e; }
    });
    return mejor;
  }

  function ajustarEscala(paso) {
    var i = ESCALAS.indexOf(escalaActual());
    i = Math.min(ESCALAS.length - 1, Math.max(0, i + paso));
    raiz.style.setProperty('--escala-lectura', ESCALAS[i]);
    guardar('lbf-escala', ESCALAS[i]);
  }

  document.addEventListener('click', function (ev) {
    var b = ev.target.closest('[data-accion]');
    if (!b) return;
    var accion = b.getAttribute('data-accion');

    if (accion === 'mas') ajustarEscala(1);
    if (accion === 'menos') ajustarEscala(-1);

    if (accion === 'modo') {
      var modo = b.getAttribute('data-modo-valor');
      raiz.setAttribute('data-modo', modo);
      guardar('lbf-modo', modo);
      document.querySelectorAll('[data-accion="modo"]').forEach(function (o) {
        o.setAttribute('aria-pressed', String(o.getAttribute('data-modo-valor') === modo));
      });
    }

    if (accion === 'copiar') {
      var lectura = document.querySelector('.lectura');
      if (!lectura || !navigator.clipboard) return;
      var ref = lectura.getAttribute('data-referencia') || '';
      var partes = [];
      lectura.querySelectorAll('.v').forEach(function (p) {
        var c = p.cloneNode(true);
        var n = c.querySelector('.vn');
        var num = n ? n.textContent.trim() : '';
        if (n) n.remove();
        partes.push((num ? num + ' ' : '') + c.textContent.trim());
      });
      navigator.clipboard.writeText(partes.join('\n') + '\n\n— ' + ref + ' (La Palabra Fiel)').then(function () {
        var previo = b.textContent;
        b.textContent = 'Copiado';
        setTimeout(function () { b.textContent = previo; }, 1600);
      });
    }
  });

  // Reflejar el estado guardado en los botones de modo al cargar.
  var modoGuardado = raiz.getAttribute('data-modo') || 'versiculos';
  document.querySelectorAll('[data-accion="modo"]').forEach(function (o) {
    o.setAttribute('aria-pressed', String(o.getAttribute('data-modo-valor') === modoGuardado));
  });

  /* ---- Copiar enlace a un versículo -------------------------------------- */
  document.addEventListener('click', function (ev) {
    var vn = ev.target.closest('.lectura .vn');
    if (!vn) return;
    var p = vn.closest('.v');
    if (p) {
      document.querySelectorAll('.lectura .v.destacado').forEach(function (o) {
        o.classList.remove('destacado');
      });
      p.classList.add('destacado');
    }
  });

  /* ---- Navegación con flechas entre capítulos ---------------------------- */
  document.addEventListener('keydown', function (ev) {
    if (ev.metaKey || ev.ctrlKey || ev.altKey) return;
    var t = ev.target;
    if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
    var sel;
    if (ev.key === 'ArrowLeft') sel = '[rel="prev"]';
    else if (ev.key === 'ArrowRight') sel = '[rel="next"]';
    else return;
    var a = document.querySelector('.nav-capitulos ' + sel);
    if (a) window.location.href = a.href;
  });

  /* ---- Buscador ---------------------------------------------------------- */
  var caja = document.getElementById('buscador');
  if (caja) iniciarBuscador(caja);

  function normalizar(s) {
    return s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  }

  function iniciarBuscador(input) {
    var estado = document.getElementById('buscador-estado');
    var salida = document.getElementById('buscador-resultados');
    var indice = null;
    var cargando = false;
    var temporizador;
    var base = input.getAttribute('data-indice');
    var baseSitio = new URL(input.getAttribute('data-base'), window.location.origin);

    function cargar() {
      if (indice || cargando) return Promise.resolve(indice);
      cargando = true;
      estado.textContent = 'Cargando el texto…';
      return fetch(base)
        .then(function (r) { return r.json(); })
        .then(function (datos) {
          indice = datos.map(function (v) {
            return {
              r: v.r,
              u: new URL(v.u.replace(/^\/+/, ''), baseSitio).href,
              t: v.t,
              n: normalizar(v.t)
            };
          });
          cargando = false;
          estado.textContent = indice.length.toLocaleString('es') + ' versículos listos para buscar.';
          return indice;
        })
        .catch(function () {
          cargando = false;
          estado.textContent = 'No se pudo cargar el índice de búsqueda.';
        });
    }

    function resaltar(texto, termino) {
      var i = normalizar(texto).indexOf(termino);
      if (i < 0) return escapar(texto);
      return escapar(texto.slice(0, i)) + '<mark>' +
        escapar(texto.slice(i, i + termino.length)) + '</mark>' +
        escapar(texto.slice(i + termino.length));
    }

    function formatearTexto(texto, termino) {
      var partes = [];
      var patron = /(^|[^*])\*([^*\n]+)\*(?!\*)/g;
      var inicio = 0;
      var coincidencia;
      while ((coincidencia = patron.exec(texto)) !== null) {
        partes.push(resaltar(texto.slice(inicio, coincidencia.index) + coincidencia[1], termino));
        partes.push('<em>' + resaltar(coincidencia[2], termino) + '</em>');
        inicio = patron.lastIndex;
      }
      partes.push(resaltar(texto.slice(inicio), termino));
      return partes.join('');
    }

    function escapar(s) {
      return s.replace(/[&<>]/g, function (c) {
        return { '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c];
      });
    }

    function buscar() {
      var q = input.value.trim();
      salida.innerHTML = '';
      if (q.length < 3) {
        estado.textContent = q.length ? 'Escribe al menos 3 caracteres.' : '';
        return;
      }
      cargar().then(function () {
        if (!indice) return;
        var termino = normalizar(q);
        var hallados = [];
        for (var i = 0; i < indice.length && hallados.length < 300; i++) {
          if (indice[i].n.indexOf(termino) !== -1) hallados.push(indice[i]);
        }
        estado.textContent = hallados.length
          ? hallados.length + (hallados.length === 300 ? '+ resultados (mostrando los primeros 300)' : ' resultado' + (hallados.length === 1 ? '' : 's'))
          : 'Sin resultados para «' + q + '».';
        var html = hallados.map(function (v) {
          return '<li><a class="ref" href="' + v.u + '">' + escapar(v.r) + '</a>' +
            '<p class="texto">' + formatearTexto(v.t, termino) + '</p></li>';
        }).join('');
        salida.innerHTML = html;
      });
    }

    input.addEventListener('input', function () {
      clearTimeout(temporizador);
      temporizador = setTimeout(buscar, 180);
    });
    input.addEventListener('focus', cargar, { once: true });

    // Permitir ?q=... en la URL
    var q = new URLSearchParams(window.location.search).get('q');
    if (q) { input.value = q; buscar(); }
    input.focus({ preventScroll: true });
  }
})();
