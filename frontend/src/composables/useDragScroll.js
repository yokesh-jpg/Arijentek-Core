import { ref, onMounted, onUnmounted } from 'vue';

export function useDragScroll() {
  const containerRef = ref(null);
  let isDown = false;
  let startX;
  let scrollLeft;

  const onMouseDown = (e) => {
    if (!containerRef.value) return;
    isDown = true;
    containerRef.value.classList.add('cursor-grabbing');
    containerRef.value.style.userSelect = 'none';
    startX = e.pageX - containerRef.value.offsetLeft;
    scrollLeft = containerRef.value.scrollLeft;
  };

  const onMouseLeave = () => {
    if (!containerRef.value) return;
    isDown = false;
    containerRef.value.classList.remove('cursor-grabbing');
    containerRef.value.style.removeProperty('user-select');
  };

  const onMouseUp = () => {
    if (!containerRef.value) return;
    isDown = false;
    containerRef.value.classList.remove('cursor-grabbing');
    containerRef.value.style.removeProperty('user-select');
  };

  const onMouseMove = (e) => {
    if (!isDown || !containerRef.value) return;
    e.preventDefault();
    const x = e.pageX - containerRef.value.offsetLeft;
    const walk = (x - startX) * 1.5; // Scroll-fast
    containerRef.value.scrollLeft = scrollLeft - walk;
  };

  const attachEvents = () => {
    if (containerRef.value) {
      containerRef.value.addEventListener('mousedown', onMouseDown);
      containerRef.value.addEventListener('mouseleave', onMouseLeave);
      containerRef.value.addEventListener('mouseup', onMouseUp);
      containerRef.value.addEventListener('mousemove', onMouseMove);
    }
  };

  const detachEvents = () => {
    if (containerRef.value) {
      containerRef.value.removeEventListener('mousedown', onMouseDown);
      containerRef.value.removeEventListener('mouseleave', onMouseLeave);
      containerRef.value.removeEventListener('mouseup', onMouseUp);
      containerRef.value.removeEventListener('mousemove', onMouseMove);
    }
  };

  onMounted(() => {
    attachEvents();
  });

  onUnmounted(() => {
    detachEvents();
  });

  return { containerRef };
}
