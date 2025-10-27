// Year stamp
document.querySelectorAll('#year').forEach(n=> n.textContent = new Date().getFullYear());

// Gallery behavior (photo carousel) on item page
(function(){
  const stage = document.getElementById('stage');
  const thumbs = document.querySelectorAll('.gallery__thumbs img');
  if (!stage || !thumbs.length) return;
  thumbs.forEach(img => {
    img.addEventListener('click', () => {
      thumbs.forEach(t => t.removeAttribute('aria-current'));
      img.setAttribute('aria-current','true');
      const large = img.getAttribute('data-large');
      const alt = img.getAttribute('alt') || '';
      stage.src = large;
      stage.alt = alt.replace('thumbnail','main image');
    });
  });
})();