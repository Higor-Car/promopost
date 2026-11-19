/* Achou Promo — pequenos comportamentos da vitrine. Tudo funciona sem JS; aqui só melhora. */
(function () {
  "use strict";

  // Aparecer suave ao rolar (respeita "reduzir movimento" do celular).
  var animaveis = document.querySelectorAll(".anima");
  var reduzir = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (!("IntersectionObserver" in window) || reduzir) {
    animaveis.forEach(function (el) { el.classList.add("visivel"); });
  } else {
    var observador = new IntersectionObserver(function (itens) {
      itens.forEach(function (item) {
        if (item.isIntersecting) {
          item.target.classList.add("visivel");
          observador.unobserve(item.target);
        }
      });
    }, { rootMargin: "0px 0px -6% 0px" });
    animaveis.forEach(function (el) { observador.observe(el); });
  }

  // Filtro escolhido sempre à vista na faixa de categorias.
  document.querySelectorAll(".chips .chip.ativo, .segmento a.ativo").forEach(function (el) {
    var faixa = el.parentElement;
    if (faixa.scrollWidth > faixa.clientWidth) {
      faixa.scrollLeft = el.offsetLeft - (faixa.clientWidth - el.offsetWidth) / 2;
    }
  });

  // Compartilhar: menu do celular quando existe; senão segue o link (WhatsApp).
  document.querySelectorAll("[data-compartilhar]").forEach(function (botao) {
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

  // Abas da página da loja: troca sem recarregar (sem JS, os links recarregam a página).
  var abas = document.querySelectorAll("[data-aba]");
  abas.forEach(function (aba) {
    aba.addEventListener("click", function (e) {
      e.preventDefault();
      abas.forEach(function (a) {
        var ativa = a === aba;
        a.setAttribute("aria-selected", ativa ? "true" : "false");
        var painel = document.getElementById(a.getAttribute("aria-controls"));
        if (painel) painel.hidden = !ativa;
      });
      if (history.replaceState) history.replaceState(null, "", aba.getAttribute("href"));
    });
  });

  // Contagem regressiva: "Acaba em 2h 15min 30s".
  var contagens = document.querySelectorAll("[data-contagem]");
  if (contagens.length) {
    var atualizar = function () {
      contagens.forEach(function (el) {
        var falta = Math.floor((new Date(el.dataset.contagem) - new Date()) / 1000);
        if (isNaN(falta)) return;
        if (falta <= 0) { el.textContent = "Promoção encerrada"; return; }
        var h = Math.floor(falta / 3600), m = Math.floor((falta % 3600) / 60), s = falta % 60;
        el.textContent = "Acaba em " + (h ? h + "h " : "") + m + "min " + (h ? "" : s + "s");
      });
    };
    atualizar();
    setInterval(atualizar, 1000);
  }
})();
