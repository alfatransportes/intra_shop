document.querySelectorAll('.carousel-wrap').forEach((wrap) => {
    const track = wrap.querySelector('.js-track');
    const prev  = wrap.querySelector('.js-prev');
    const next  = wrap.querySelector('.js-next');
  
    if (!track || !prev || !next) return;
  
    function cardStep() {
      const card = track.querySelector('.card-section');
      if (!card) return 300;
  
      const styles = getComputedStyle(track);
      const gap = parseFloat(styles.columnGap || styles.gap || '0');
  
      return card.getBoundingClientRect().width + gap;
    }
  
    function updateArrows() {
      const maxScroll = track.scrollWidth - track.clientWidth;
      const tolerance = 2;
  
      prev.style.display = track.scrollLeft <= tolerance ? 'none' : 'grid';
      next.style.display = track.scrollLeft >= maxScroll - tolerance ? 'none' : 'grid';
    }
  
    prev.addEventListener('click', () => {
      track.scrollBy({ left: -cardStep(), behavior: 'smooth' });
    });
  
    next.addEventListener('click', () => {
      track.scrollBy({ left: cardStep(), behavior: 'smooth' });
    });
  
    track.addEventListener('scroll', updateArrows);
    window.addEventListener('resize', updateArrows);
  
    // inicializa
    updateArrows();
  });
  