// Minimal JS: no heavy behavior. Provide utilities for confirmation if needed.
document.addEventListener('DOMContentLoaded', function(){
  // placeholder for future enhancements (filters handled by server)
  // Featured carousel
  const carousel = document.querySelector('.featured-carousel');
  if (carousel) {
    const track = carousel.querySelector('.carousel-track');
    const items = Array.from(track.querySelectorAll('.carousel-item'));
    let idx = 0;
    const show = (i) => {
      items.forEach((it, j) => it.classList.toggle('active', j === i));
    };
    if (items.length > 0) show(0);

    const next = () => { idx = (idx + 1) % items.length; show(idx); };
    const prev = () => { idx = (idx - 1 + items.length) % items.length; show(idx); };

    let timer = setInterval(next, 4000);
    carousel.addEventListener('mouseenter', () => clearInterval(timer));
    carousel.addEventListener('mouseleave', () => { clearInterval(timer); timer = setInterval(next, 4000); });

    const btnNext = carousel.querySelector('.carousel-next');
    const btnPrev = carousel.querySelector('.carousel-prev');
    if (btnNext) btnNext.addEventListener('click', (e)=>{ e.preventDefault(); next(); });
    if (btnPrev) btnPrev.addEventListener('click', (e)=>{ e.preventDefault(); prev(); });
  }
  // Lightbox for about gallery
  const lightbox = document.getElementById('lightbox');
  if (lightbox) {
    const imgEl = lightbox.querySelector('.lightbox-img');
    const closeBtn = lightbox.querySelector('.lightbox-close');
    document.querySelectorAll('.gallery-item').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const src = btn.getAttribute('data-src');
        imgEl.src = src;
        lightbox.setAttribute('aria-hidden', 'false');
      });
    });
    function closeLB(){ lightbox.setAttribute('aria-hidden','true'); imgEl.src=''; }
    closeBtn.addEventListener('click', closeLB);
    lightbox.addEventListener('click', (e)=>{ if (e.target === lightbox) closeLB(); });
  }
});
