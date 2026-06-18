// =====================================================
// EoA Printing — Main JS
// =====================================================

// Mobile nav toggle
const navToggle = document.getElementById('navToggle');
const nav = document.getElementById('nav');
if (navToggle && nav) {
    navToggle.addEventListener('click', () => {
        nav.classList.toggle('open');
    });
    // Chiudi nav su click di un link
    nav.querySelectorAll('a').forEach(a => {
        a.addEventListener('click', () => nav.classList.remove('open'));
    });
}

// Cookie banner
const COOKIE_KEY = 'eoa_cookies_accepted';
const banner = document.getElementById('cookieBanner');
if (banner) {
    if (localStorage.getItem(COOKIE_KEY) === 'yes') {
        banner.classList.add('hidden');
    } else {
        banner.classList.remove('hidden');
    }
}
function acceptCookies() {
    localStorage.setItem(COOKIE_KEY, 'yes');
    if (banner) banner.classList.add('hidden');
}
window.acceptCookies = acceptCookies;

// Smooth scroll fallback per browser vecchi (CSS lo fa già)
document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', (e) => {
        const target = document.querySelector(a.getAttribute('href'));
        if (target) {
            e.preventDefault();
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    });
});

// Animazione fade-in on scroll (semplice)
const fadeObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
        }
    });
}, { threshold: 0.1 });

document.querySelectorAll('.servizio, .portfolio__item, .step, .contact-card').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(20px)';
    el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
    fadeObserver.observe(el);
});
