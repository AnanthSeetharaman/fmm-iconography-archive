/**
 * Five Metal Masonry (FMM) — Sacred Bronze Iconography Archive
 * Three.js WebGL 3D Sacred Bronze Gallery Engine (gallery_3d.js)
 * 
 * Implements an interactive 3D spatial exhibition gallery featuring:
 * - Panchaloha 5-Metal Alloy PBR Shaders & Metallic Reflectivity
 * - 3D Floating Carousel Plates mounted in Archival Bronze Pedestals
 * - Rotating Dharmachakra Iconometric Halos around active slides
 * - Interactive Mouse/Touch Orbital Navigation, Tilt, & Smooth Focus Lerp
 * - Atmospheric Sacred Lighting (Temple Key Light, Ambient Gold, Rim Light)
 * - Dynamic Sync with Frontend Slide Viewer & OCR Extraction Panels
 */

class FMMBronzeGallery3D {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        if (!this.container) return;

        this.options = Object.assign({
            onSlideSelect: null,
            autoRotate: true,
            theme: 'parchment'
        }, options);

        this.slidesData = [];
        this.slideMeshes = [];
        this.haloMeshes = [];
        this.activeIndex = 0;
        this.isInitialized = false;

        // Three.js Core Components
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.textureLoader = new THREE.TextureLoader();

        // Interaction State
        this.isDragging = false;
        this.previousMousePosition = { x: 0, y: 0 };
        this.targetRotationY = 0;
        this.targetRotationX = 0;
        this.currentRotationY = 0;
        this.currentRotationX = 0;
        this.targetCameraZ = 7.5;
        this.currentCameraZ = 7.5;

        // Raycasting for 3D object interaction
        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();

        this.init();
    }

    init() {
        if (this.isInitialized) return;

        // 1. Scene Setup
        this.scene = new THREE.Scene();

        // 2. Camera Setup
        const aspect = this.container.clientWidth / this.container.clientHeight || 16/9;
        this.camera = new THREE.PerspectiveCamera(42, aspect, 0.1, 100);
        this.camera.position.set(0, 0.5, this.currentCameraZ);

        // 3. Renderer Setup
        this.renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, powerPreference: "high-performance" });
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;

        // Clean container and attach canvas
        this.container.innerHTML = '';
        this.container.appendChild(this.renderer.domElement);

        // 4. Atmospheric Sacred Lighting
        this.setupLighting();

        // 5. Ambient Particles (Sacred Temple Dust Motes)
        this.setupParticles();

        // 6. Bind Event Listeners
        this.bindEvents();

        this.isInitialized = true;
        this.animate();
    }

    setupLighting() {
        // Warm Temple Ambient Light
        const ambientLight = new THREE.AmbientLight(0xfff5e6, 1.4);
        this.scene.add(ambientLight);

        // Directional Key Light (Gold/Bronze Highlight)
        const keyLight = new THREE.DirectionalLight(0xd4a359, 2.5);
        keyLight.position.set(6, 8, 6);
        keyLight.castShadow = true;
        keyLight.shadow.mapSize.width = 1024;
        keyLight.shadow.mapSize.height = 1024;
        this.scene.add(keyLight);

        // Warm Fill Light
        const fillLight = new THREE.PointLight(0xb75b34, 2.0, 15);
        fillLight.position.set(-6, -2, 4);
        this.scene.add(fillLight);

        // Back Rim Light for Antique Edge Glow
        const rimLight = new THREE.DirectionalLight(0xffd79e, 1.5);
        rimLight.position.set(0, 5, -8);
        this.scene.add(rimLight);
    }

    setupParticles() {
        const particleCount = 120;
        const geometry = new THREE.BufferGeometry();
        const positions = new Float32Array(particleCount * 3);

        for (let i = 0; i < particleCount * 3; i += 3) {
            positions[i] = (Math.random() - 0.5) * 15;
            positions[i + 1] = (Math.random() - 0.5) * 10;
            positions[i + 2] = (Math.random() - 0.5) * 15;
        }

        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

        const material = new THREE.PointsMaterial({
            color: 0xd4af37,
            size: 0.06,
            transparent: true,
            opacity: 0.45,
            blending: THREE.AdditiveBlending
        });

        this.particleSystem = new THREE.Points(geometry, material);
        this.scene.add(this.particleSystem);
    }

    loadSlides(slides) {
        if (!slides || slides.length === 0) return;
        this.slidesData = slides;

        // Clear existing slide meshes
        this.slideMeshes.forEach(mesh => this.scene.remove(mesh));
        this.haloMeshes.forEach(halo => this.scene.remove(halo));
        this.slideMeshes = [];
        this.haloMeshes = [];

        const radius = Math.max(3.2, slides.length * 0.7);
        const angleStep = (Math.PI * 0.85) / Math.max(1, slides.length - 1);
        const startAngle = - (Math.PI * 0.85) / 2;

        slides.forEach((slide, idx) => {
            const angle = slides.length === 1 ? 0 : startAngle + idx * angleStep;
            
            // 3D Frame & Canvas Geometry
            const group = new THREE.Group();
            
            // Panchaloha 5-Metal Alloy Frame Material
            const bronzeMaterial = new THREE.MeshStandardMaterial({
                color: 0xc29b38,
                roughness: 0.25,
                metalness: 0.88,
            });

            // Pedestal Frame (Outer Border)
            const frameGeo = new THREE.BoxGeometry(2.4, 3.2, 0.12);
            const frameMesh = new THREE.Mesh(frameGeo, bronzeMaterial);
            frameMesh.castShadow = true;
            frameMesh.receiveShadow = true;
            group.add(frameMesh);

            // Inner Plate Base (Paper / Bronze Canvas)
            const innerGeo = new THREE.PlaneGeometry(2.18, 2.98);
            
            // Load Texture or Procedural Placeholder
            let innerMat;
            if (slide.image_url) {
                const texture = this.textureLoader.load(
                    slide.image_url,
                    () => { this.renderer.render(this.scene, this.camera); },
                    undefined,
                    () => {
                        // Fallback canvas texture if image fails
                        innerMat = this.createFallbackTextureMaterial(slide.slide_title || `Plate ${idx + 1}`);
                        innerMesh.material = innerMat;
                    }
                );
                texture.generateMipmaps = true;
                texture.minFilter = THREE.LinearMipmapLinearFilter;

                innerMat = new THREE.MeshStandardMaterial({
                    map: texture,
                    roughness: 0.4,
                    metalness: 0.1
                });
            } else {
                innerMat = this.createFallbackTextureMaterial(slide.slide_title || `Plate ${idx + 1}`);
            }

            const innerMesh = new THREE.Mesh(innerGeo, innerMat);
            innerMesh.position.z = 0.07;
            group.add(innerMesh);

            // Rotating Dharmachakra Iconometric Halo Ring around plate
            const haloGeo = new THREE.TorusGeometry(1.85, 0.03, 16, 64);
            const haloMat = new THREE.MeshStandardMaterial({
                color: 0xd4af37,
                roughness: 0.2,
                metalness: 0.95,
                transparent: true,
                opacity: 0.6
            });
            const haloMesh = new THREE.Mesh(haloGeo, haloMat);
            haloMesh.position.z = 0.02;
            group.add(haloMesh);
            this.haloMeshes.push(haloMesh);

            // Positioning in Arc Formation
            group.position.x = Math.sin(angle) * radius;
            group.position.z = Math.cos(angle) * (radius * 0.5) - (radius * 0.3);
            group.rotation.y = angle * 0.7;

            group.userData = { slideIndex: idx, slideData: slide };
            this.scene.add(group);
            this.slideMeshes.push(group);
        });

        this.setActiveSlide(0, false);
    }

    createFallbackTextureMaterial(title) {
        const canvas = document.createElement('canvas');
        canvas.width = 512;
        canvas.height = 700;
        const ctx = canvas.getContext('2d');

        // Parchment Gradient
        const grad = ctx.createLinearGradient(0, 0, 512, 700);
        grad.addColorStop(0, '#f5eee1');
        grad.addColorStop(1, '#e3d4be');
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, 512, 700);

        // Antique Border
        ctx.strokeStyle = '#b75b34';
        ctx.lineWidth = 12;
        ctx.strokeRect(20, 20, 472, 660);

        ctx.strokeStyle = '#c29b38';
        ctx.lineWidth = 4;
        ctx.strokeRect(32, 32, 448, 636);

        // Title Copy
        ctx.fillStyle = '#1c2024';
        ctx.font = 'bold 32px Georgia, serif';
        ctx.textAlign = 'center';
        ctx.fillText('FIVE METAL MASONRY', 256, 120);

        ctx.fillStyle = '#b75b34';
        ctx.font = 'italic 22px Inter, sans-serif';
        ctx.fillText('SACRED BRONZE ARCHIVE', 256, 160);

        ctx.fillStyle = '#4a443b';
        ctx.font = '24px Georgia, serif';
        ctx.fillText(title, 256, 360);

        const texture = new THREE.CanvasTexture(canvas);
        return new THREE.MeshStandardMaterial({ map: texture, roughness: 0.4 });
    }

    setActiveSlide(index, triggerCallback = true) {
        if (index < 0 || index >= this.slideMeshes.length) return;

        this.activeIndex = index;

        this.slideMeshes.forEach((mesh, idx) => {
            const isTarget = idx === index;
            
            // Animate position elevation & rotation focus
            const targetZ = isTarget ? 1.2 : 0;
            const targetScale = isTarget ? 1.12 : 0.95;

            mesh.position.y = isTarget ? 0.3 : 0;
            mesh.scale.set(targetScale, targetScale, targetScale);

            // Halo opacity & highlight
            if (this.haloMeshes[idx]) {
                this.haloMeshes[idx].material.opacity = isTarget ? 0.9 : 0.3;
                this.haloMeshes[idx].material.color.setHex(isTarget ? 0xffd700 : 0xc29b38);
            }
        });

        // Rotate arc to center active slide
        if (this.slideMeshes[index]) {
            this.targetRotationY = -this.slideMeshes[index].position.x * 0.35;
        }

        if (triggerCallback && typeof this.options.onSlideSelect === 'function') {
            this.options.onSlideSelect(index, this.slidesData[index]);
        }
    }

    bindEvents() {
        const dom = this.renderer.domElement;

        // Pointer / Touch Handlers
        dom.addEventListener('pointerdown', (e) => {
            this.isDragging = true;
            this.previousMousePosition = { x: e.clientX, y: e.clientY };
        });

        window.addEventListener('pointermove', (e) => {
            if (!this.isDragging) return;
            const deltaX = e.clientX - this.previousMousePosition.x;
            const deltaY = e.clientY - this.previousMousePosition.y;

            this.targetRotationY += deltaX * 0.005;
            this.targetRotationX += deltaY * 0.003;
            this.targetRotationX = Math.max(-0.4, Math.min(0.4, this.targetRotationX));

            this.previousMousePosition = { x: e.clientX, y: e.clientY };
        });

        window.addEventListener('pointerup', (e) => {
            if (this.isDragging) {
                this.isDragging = false;
            }
        });

        // Click selection via Raycaster
        dom.addEventListener('click', (e) => {
            const rect = dom.getBoundingClientRect();
            this.mouse.x = ((e.clientX - rect.left) / dom.clientWidth) * 2 - 1;
            this.mouse.y = -((e.clientY - rect.top) / dom.clientHeight) * 2 + 1;

            this.raycaster.setFromCamera(this.mouse, this.camera);
            const intersects = this.raycaster.intersectObjects(this.scene.children, true);

            for (let hit of intersects) {
                let curr = hit.object;
                while (curr && !curr.userData.slideData) {
                    curr = curr.parent;
                }
                if (curr && curr.userData.slideIndex !== undefined) {
                    this.setActiveSlide(curr.userData.slideIndex, true);
                    break;
                }
            }
        });

        // Responsive Resize
        window.addEventListener('resize', () => {
            if (!this.container || this.container.clientWidth === 0) return;
            this.camera.aspect = this.container.clientWidth / this.container.clientHeight;
            this.camera.updateProjectionMatrix();
            this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
        });
    }

    animate() {
        requestAnimationFrame(() => this.animate());

        // Smooth Lerp Rotations
        this.currentRotationY += (this.targetRotationY - this.currentRotationY) * 0.05;
        this.currentRotationX += (this.targetRotationX - this.currentRotationX) * 0.05;

        this.scene.rotation.y = this.currentRotationY;
        this.scene.rotation.x = this.currentRotationX;

        // Continuous Halo Rotation
        this.haloMeshes.forEach((halo, idx) => {
            halo.rotation.z += idx % 2 === 0 ? 0.008 : -0.006;
        });

        // Particle Drift
        if (this.particleSystem) {
            this.particleSystem.rotation.y += 0.001;
        }

        this.renderer.render(this.scene, this.camera);
    }
}

// Export to Global Scope
window.FMMBronzeGallery3D = FMMBronzeGallery3D;
