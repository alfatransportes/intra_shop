document.addEventListener('DOMContentLoaded', function () {
    /* --------- Reveal --------- */
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) entry.target.classList.add('in');
            else entry.target.classList.remove('in');
        });
    }, { root: null, threshold: 0.25, rootMargin: '-8% 0% -8% 0%' });

    document.querySelectorAll('.reveal').forEach(el => observer.observe(el));

    window.addEventListener('hashchange', () =>
        setTimeout(() => observer.takeRecords(), 50),
    { passive: true });

    /* --------- Dock visibilidade --------- */
    const dock = document.querySelector('.menu-nav');
    const home = document.getElementById('home');

    function toggleDock() {
        if (!dock) return;
        if (!home) {
            dock.classList.add('visible');
            dock.setAttribute('aria-hidden', 'false');
            return;
        }
        const rect = home.getBoundingClientRect();
        const viewportHeight = window.innerHeight || document.documentElement.clientHeight;
        const isHomeVisible = rect.top < viewportHeight && rect.bottom > 0;
        dock.classList.toggle('visible', !isHomeVisible);
        dock.setAttribute('aria-hidden', isHomeVisible ? 'true' : 'false');
    }

    window.addEventListener('scroll', toggleDock, { passive: true });
    window.addEventListener('resize', toggleDock, { passive: true });
    window.addEventListener('load', toggleDock, { passive: true });
    toggleDock();

    /* --------- Navbar sólida/oculta --------- */
    const mainNav = document.getElementById('mainNav');
    if (mainNav) {
        let lastY = window.scrollY;
        const solidAt = 10;

        const onScroll = () => {
            const y = window.scrollY;

            // navbar sólida
            if (y > solidAt) mainNav.classList.add('navbar-solid');
            else mainNav.classList.remove('navbar-solid');

            // navbar oculta em desktop
            if (window.innerWidth >= 992) {
                if (y > lastY && y > 120) mainNav.classList.add('navbar-hidden');
                else mainNav.classList.remove('navbar-hidden');
            }

            lastY = y;
            toggleDock();
        };

        document.addEventListener('scroll', onScroll, { passive: true });
        onScroll();
    }

    /* --------- Mega: fechar no mobile --------- */
    document.querySelectorAll('.dropdown-menu.mega .btn-close-mobile').forEach(btn => {
        btn.addEventListener('click', () => {
            const dd = btn.closest('.dropdown-menu');
            const toggle = dd?.parentElement?.querySelector('[data-bs-toggle="dropdown"]');
            if (toggle) bootstrap.Dropdown.getOrCreateInstance(toggle).hide();
        });
    });

    /* --------- Fecha dropdown ao navegar por âncora --------- */
    document.querySelectorAll('a[href^="#"]:not([data-bs-toggle])')
    .forEach(a => {
        a.addEventListener('click', () => {
            document.querySelectorAll('.dropdown-menu.show')
                .forEach(dm => dm.classList.remove('show'));
        });
    });

    /* --------- Page Loader --------- */
    const containers = document.querySelectorAll(".page-loader");
    const bars = document.querySelectorAll(".page-loader-bar");

    if (containers.length && bars.length) {
        let progress = 0;

        const timer = setInterval(() => {
            if (progress < 80) {
                progress += 5;
                bars.forEach(bar => bar.style.width = progress + "%");
            } else {
                clearInterval(timer);
            }
        }, 150);

        window.addEventListener("load", function () {
            progress = 100;

            bars.forEach(bar => bar.style.width = "100%");

            setTimeout(() => {
                containers.forEach(container => {
                    container.style.transition = "opacity .3s ease";
                    container.style.opacity = "0";

                    setTimeout(() => container.remove(), 300);
                });
            }, 300);
        });
    }

    /* --------- Consentimento / Offcanvas / Cookies (SILENCIOSO) --------- */
    const consentBanner = document.getElementById('consentBanner');
    const offcanvasEl = document.getElementById('consentOffcanvas');

    // só inicializa se existir no DOM
    if (consentBanner && offcanvasEl) {
        const offcanvas = new bootstrap.Offcanvas(offcanvasEl);

        const btnGerenciar = document.getElementById('btnGerenciar');
        const btnConfigurar = document.getElementById('btnConfigurar');
        const btnAceitarTudo = document.getElementById('btnAceitarTudo');
        const btnRecusarTudo = document.getElementById('btnRecusarTudo');
        const btnSalvarPrefs = document.getElementById('btnSalvarPrefs');

        const consentGeo = document.getElementById('consentGeo');
        const selectAllImages = document.getElementById('selectAllImages');
        const imgCheckboxes = document.querySelectorAll('.img-opt');

        // Cookies
        function setCookie(name, value, days = 365) {
            const expires = new Date(Date.now() + days * 24 * 60 * 60 * 1000).toUTCString();
            document.cookie = `${name}=${encodeURIComponent(value)}; Expires=${expires}; Path=/; Secure; SameSite=Lax`;
        }
        function getCookie(name) {
            const m = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
            return m ? decodeURIComponent(m[2]) : null;
        }
        function eraseCookie(name) {
            document.cookie = `${name}=; Expires=Thu, 01 Jan 1970 00:00:00 GMT; Path=/; Secure; SameSite=Lax`;
        }

        function showBanner(show) {
            consentBanner.classList.toggle('d-none', !show);
            if (dock) dock.classList.toggle('d-none', show);
        }

        function hydrateFromCookie() {
            const prefsStr = getCookie('consent_prefs');
            if (!prefsStr) return;
            try {
                const prefs = JSON.parse(prefsStr);
                if (consentGeo) consentGeo.checked = !!prefs.geolocation;

                const map = {
                    imgPerfil: 'profileDisplay',
                    imgListagensPublicas: 'publicListings',
                    imgUploads: 'uploads',
                    imgAnalise: 'aiAnalysis',
                    imgParceiros: 'partnerSharing',
                };
                Object.entries(map).forEach(([id, key]) => {
                    const el = document.getElementById(id);
                    if (el && prefs.imagePolicy && key in prefs.imagePolicy) {
                        el.checked = !!prefs.imagePolicy[key];
                    }
                });
                if (selectAllImages) {
                    selectAllImages.checked = Array.from(imgCheckboxes).every(x => x.checked);
                }
            } catch { }
        }

        function collectPrefs(forceAll = false) {
            const imagePolicy = {
                profileDisplay: forceAll ? true : document.getElementById('imgPerfil').checked,
                publicListings: forceAll ? true : document.getElementById('imgListagensPublicas').checked,
                uploads: forceAll ? true : document.getElementById('imgUploads').checked,
                aiAnalysis: forceAll ? true : document.getElementById('imgAnalise').checked,
                partnerSharing: forceAll ? true : document.getElementById('imgParceiros').checked
            };
            const geoAllowed = forceAll ? true : (consentGeo ? consentGeo.checked : false);
            return {
                termsAccepted: true,
                geolocation: geoAllowed,
                imagePolicy,
                ts: new Date().toISOString()
            };
        }

        function savePrefs(prefs) {
            setCookie('consent_prefs', JSON.stringify(prefs), 365);
        }

        async function maybeAskGeolocation(prefs) {
            if (!prefs.geolocation) return;
            if (!('geolocation' in navigator)) return;
            try {
                const pos = await new Promise((resolve, reject) => {
                    navigator.geolocation.getCurrentPosition(resolve, reject, {
                        enableHighAccuracy: true, timeout: 10000, maximumAge: 0
                    });
                });
                const coords = {
                    latitude: pos.coords.latitude,
                    longitude: pos.coords.longitude,
                    accuracy: pos.coords.accuracy,
                    timestamp: new Date(pos.timestamp).toISOString()
                };
                setCookie('user_location', JSON.stringify(coords), 1);
            } catch { }
        }

        if (btnGerenciar) {
            btnGerenciar.addEventListener('click', () => {
                hydrateFromCookie();
                offcanvas.show();
            });
        }

        if (selectAllImages) {
            selectAllImages.addEventListener('change', (e) => {
                imgCheckboxes.forEach(c => c.checked = e.target.checked);
            });
        }

        imgCheckboxes.forEach(c => {
            c.addEventListener('change', () => {
                if (selectAllImages) {
                    selectAllImages.checked = Array.from(imgCheckboxes).every(x => x.checked);
                }
            });
        });

        if (btnAceitarTudo) {
            btnAceitarTudo.addEventListener('click', async () => {
                const prefs = collectPrefs(true);
                savePrefs(prefs);
                await maybeAskGeolocation(prefs);
                showBanner(false);
                window.location.reload();
            });
        }

        if (btnRecusarTudo) {
            btnRecusarTudo.addEventListener('click', () => {
                const prefs = {
                    termsAccepted: false,
                    geolocation: false,
                    imagePolicy: {
                        profileDisplay: false,
                        publicListings: false,
                        uploads: false,
                        aiAnalysis: false,
                        partnerSharing: false
                    },
                    ts: new Date().toISOString()
                };
                setCookie('consent_prefs', JSON.stringify(prefs), 365);
                showBanner(false);
            });
        }

        if (btnSalvarPrefs) {
            btnSalvarPrefs.addEventListener('click', async () => {
                const prefs = collectPrefs(false);
                savePrefs(prefs);
                await maybeAskGeolocation(prefs);
                offcanvas.hide();
                showBanner(false);
                window.location.reload();
            });
        }

        (function init() {
            const hasPrefs = !!getCookie('consent_prefs');
            showBanner(!hasPrefs);
            hydrateFromCookie();
        })();
    }
});
