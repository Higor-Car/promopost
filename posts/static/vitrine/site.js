/* Achou Promo — pequenos comportamentos da vitrine. Tudo funciona sem JS; aqui só deixa mais suave. */
(function () {
  "use strict";

  var reduzir = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var observador = null;
  if ("IntersectionObserver" in window && !reduzir) {
    observador = new IntersectionObserver(function (itens) {
      itens.forEach(function (item) {
        if (item.isIntersecting) {
          item.target.classList.add("visivel");
          observador.unobserve(item.target);
        }
      });
    }, { rootMargin: "0px 0px -4% 0px" });
  }

  var relogio = null;

  // Liga os comportamentos dentro de `raiz` (a página toda, ou o conteúdo trocado).
  function iniciar(raiz) {
    // Aparecer suave ao rolar.
    raiz.querySelectorAll(".anima").forEach(function (el) {
      if (observador) observador.observe(el); else el.classList.add("visivel");
    });

    // Filtro escolhido sempre à vista na faixa rolável.
    raiz.querySelectorAll(".chips .chip.ativo, .segmento a.ativo").forEach(function (el) {
      var faixa = el.parentElement;
      if (faixa.scrollWidth > faixa.clientWidth) {
        faixa.scrollLeft = el.offsetLeft - (faixa.clientWidth - el.offsetWidth) / 2;
      }
    });

    // Compartilhar: menu do celular quando existe; senão segue o link (WhatsApp).
    raiz.querySelectorAll("[data-compartilhar]").forEach(function (botao) {
      botao.addEventListener("click", function (e) {
        if (!navigator.share) return;
        e.preventDefault();
        navigator.share({
          title: botao.dataset.titulo || document.title,
          text: botao.dataset.texto || "",
          url: botao.dataset.url || location.href
        }).catch(function () {});
      });
    });

    // Abas da página da loja: troca sem recarregar.
    var abas = raiz.querySelectorAll("[data-aba]");
    abas.forEach(function (aba) {
      aba.addEventListener("click", function (e) {
        e.preventDefault();
        abas.forEach(function (a) {
          var ativa = a === aba;
          a.setAttribute("aria-selected", ativa ? "true" : "false");
          var painel = document.getElementById(a.getAttribute("aria-controls"));
          if (painel) painel.hidden = !ativa;
        });
        if (history.replaceState) history.replaceState(history.state, "", aba.getAttribute("href").split("#")[0]);
      });
    });

    // Contagem regressiva: "Acaba em 2h 15min".
    var contagens = document.querySelectorAll("[data-contagem]");
    if (relogio) { clearInterval(relogio); relogio = null; }
    if (contagens.length) {
      var atualizar = function () {
        contagens.forEach(function (el) {
          var falta = Math.floor((new Date(el.dataset.contagem) - new Date()) / 1000);
          if (isNaN(falta)) return;
          if (falta <= 0) { el.textContent = "Promoção encerrada"; return; }
          var h = Math.floor(falta / 3600), m = Math.floor((falta % 3600) / 60), s = falta % 60;
          el.textContent = "Acaba em " + (h ? h + "h " : "") + m + "min" + (h ? "" : " " + s + "s");
        });
      };
      atualizar();
      relogio = setInterval(atualizar, 1000);
    }
  }

  // Navegação suave: troca de cidade/categoria sem recarregar a página nem voltar ao topo.
  var principal = document.querySelector("main");
  var pedidoAtual = 0;

  function navegar(url, empilhar) {
    var numero = ++pedidoAtual;
    principal.classList.add("carregando");
    fetch(url, { headers: { "X-Requested-With": "fetch" }, credentials: "same-origin" })
      .then(function (resposta) {
        if (!resposta.ok) throw new Error(resposta.status);
        return resposta.text();
      })
      .then(function (html) {
        if (numero !== pedidoAtual) return; // um clique mais novo já está a caminho
        var doc = new DOMParser().parseFromString(html, "text/html");
        var novo = doc.querySelector("main");
        if (!novo) throw new Error("sem conteúdo");
        var trocar = function () {
          principal.innerHTML = novo.innerHTML;
          document.title = doc.title;
          var buscaNova = doc.querySelector(".topo .busca"), buscaAtual = document.querySelector(".topo .busca");
          if (buscaNova && buscaAtual) buscaAtual.replaceWith(buscaNova);
          if (empilhar) history.pushState({ suave: true }, "", url);
          principal.classList.remove("carregando");
          iniciar(principal);
        };
        if (document.startViewTransition && !reduzir) document.startViewTransition(trocar);
        else trocar();
      })
      .catch(function () { location.href = url; });
  }

  if (principal && window.fetch && window.history && history.pushState) {
    document.addEventListener("click", function (e) {
      var link = e.target.closest("a[data-suave]");
      if (!link || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      if (link.origin !== location.origin) return;
      e.preventDefault();
      navegar(link.href, true);
    });
    history.replaceState({ suave: true }, "", location.href);
    window.addEventListener("popstate", function (e) {
      if (e.state && e.state.suave) navegar(location.href, false);
    });
  }

  // Tema claro / escuro: o novo tema se abre num círculo a partir do botão.
  var botaoTema = document.querySelector(".tema");
  var raiz = document.documentElement;
  function aplicarTema(tema) {
    raiz.setAttribute("data-tema", tema);
    try { localStorage.setItem("tema", tema); } catch (e) {}
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", tema === "escuro" ? "#13110f" : "#fff7ef");
    if (botaoTema) botaoTema.setAttribute("aria-pressed", tema === "escuro" ? "true" : "false");
  }
  if (botaoTema) {
    botaoTema.setAttribute("aria-pressed", raiz.getAttribute("data-tema") === "escuro" ? "true" : "false");
    botaoTema.addEventListener("click", function () {
      var novo = raiz.getAttribute("data-tema") === "escuro" ? "claro" : "escuro";
      if (!document.startViewTransition || reduzir) { aplicarTema(novo); return; }
      var r = botaoTema.getBoundingClientRect();
      var x = r.left + r.width / 2, y = r.top + r.height / 2;
      var raio = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
      raiz.classList.add("trocando-tema");
      var transicao = document.startViewTransition(function () { aplicarTema(novo); });
      transicao.ready.then(function () {
        raiz.animate(
          { clipPath: ["circle(0px at " + x + "px " + y + "px)", "circle(" + raio + "px at " + x + "px " + y + "px)"] },
          { duration: 550, easing: "cubic-bezier(.4, 0, .2, 1)", pseudoElement: "::view-transition-new(root)" }
        );
      });
      transicao.finished.finally(function () { raiz.classList.remove("trocando-tema"); });
    });
  }

  iniciar(document);
})();
