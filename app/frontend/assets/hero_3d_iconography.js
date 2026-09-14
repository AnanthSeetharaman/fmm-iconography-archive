/**
 * Five Metal Masonry (FMM) — Sacred Bronze Iconography Archive
 * Three.js WebGL Interactive Sacred Tablet Engine (hero_3d_iconography.js)
 * 
 * Features:
 * - High-Resolution Textured 3D Panchaloha Bronze Tablet (Shiva & Ganesha)
 * - Official Five Metal Masonry Brand Medallion on the reverse side
 * - Dual Rotating Sacred Dharmachakra / Mandala Orbit Rings
 * - Celestial Golden Dust Particle Field (Atmospheric Sacred Motes)
 * - Calibrated Museum Lighting with ACES Filmic Tone Mapping (Deep Blacks, Zero Glare)
 * - Responsive Mouse Parallax Tilt & 360-Degree Interactive Drag
 * - Real-Time Dark / Light Mode Lighting & Specular Transitions
 */

class FMMHeroIconography3D {
  constructor(containerId, options = {}) {
    this.container = document.getElementById(containerId);
    if (!this.container) return;

    this.options = Object.assign({
      imageUrl: 'assets/shilpa_shastra_iconography.png',
      reverseUrl: 'assets/shilpa_shastra_reverse.png',
      aspectRatio: 16 / 9,
      autoRotate: true
    }, options);

    this.scene = null;
    this.camera = null;
    this.renderer = null;
    this.tabletGroup = null;
    this.haloGroup = null;
    this.particles = null;

    // Lights
    this.ambientLight = null;
    this.keyLight = null;
    this.shivaFill = null;
    this.ganeshaFill = null;
    this.rimLight = null;

    // Materials
    this.frontMaterial = null;
    this.backMaterial = null;
    this.frameMaterial = null;
    this.haloMaterial1 = null;
    this.haloMaterial2 = null;

    // Interaction Tracking
    this.isDragging = false;
    this.previousMousePosition = { x: 0, y: 0 };
    this.targetRotationY = 0;
    this.targetRotationX = 0;
    this.currentRotationY = 0;
    this.currentRotationX = 0;
    this.parallaxX = 0;
    this.parallaxY = 0;
    this.targetParallaxX = 0;
    this.targetParallaxY = 0;

    this.clock = new THREE.Clock();
    this.animationFrameId = null;
    this.isInitialized = false;

    this.init();
  }

  init() {
    if (this.isInitialized) return;
    if (typeof THREE === 'undefined') {
      console.warn('[Hero3D] Three.js not loaded. Retrying in 200ms...');
      setTimeout(() => this.init(), 200);
      return;
    }

    const width = this.container.clientWidth || 480;
    const height = this.container.clientHeight || 340;

    // 1. Scene
    this.scene = new THREE.Scene();

    // 2. Camera
    const aspect = width / height;
    this.camera = new THREE.PerspectiveCamera(36, aspect, 0.1, 50);
    this.camera.position.set(0, 0, 6.2);

    // 3. Renderer with ACES Filmic Tone Mapping for authentic depth & non-washed-out contrast
    this.renderer = new THREE.WebGLRenderer({
      alpha: true,
      antialias: true,
      powerPreference: 'high-performance'
    });
    this.renderer.setSize(width, height);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.outputEncoding = THREE.sRGBEncoding;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.0;

    this.container.innerHTML = '';
    this.container.appendChild(this.renderer.domElement);

    // 4. Lighting Rig
    this.setupLighting();

    // 5. Build 3D Sacred Bronze Tablet
    this.buildTablet();

    // 6. Sacred Orbit Halos
    this.buildHalos();

    // 7. Celestial Dust Particles
    this.buildParticles();

    // 8. Event Listeners
    this.bindEvents();

    // 9. Sync with Theme
    this.syncTheme(document.documentElement.getAttribute('data-theme') || 'light');

    // 10. Start Animation Loop
    this.isInitialized = true;
    this.animate();
  }

  setupLighting() {
    // Ambient Light: Soft warm baseline preserving inky obsidian shadows without milky gray wash
    this.ambientLight = new THREE.AmbientLight(0xfff8ee, 0.40);
    this.scene.add(this.ambientLight);

    // Central Key Light: Calibrated warm directional light
    this.keyLight = new THREE.DirectionalLight(0xfff5ea, 1.05);
    this.keyLight.position.set(2.5, 3.5, 4.0);
    this.scene.add(this.keyLight);

    // Shiva Left Fill Light (Patina turquoise hint)
    this.shivaFill = new THREE.PointLight(0x38bdf8, 0.38, 10);
    this.shivaFill.position.set(-3.2, 0.5, 2.8);
    this.scene.add(this.shivaFill);

    // Ganesha Right Fill Light (Warm golden brass hint)
    this.ganeshaFill = new THREE.PointLight(0xf59e0b, 0.48, 10);
    this.ganeshaFill.position.set(3.2, 0.5, 2.8);
    this.scene.add(this.ganeshaFill);

    // Rim Light (Sacred backlight grazing bronze frame edges)
    this.rimLight = new THREE.DirectionalLight(0xc29b38, 0.60);
    this.rimLight.position.set(0, 3, -4);
    this.scene.add(this.rimLight);
  }

  createSthapatiGridTexture() {
    const canvas = document.createElement('canvas');
    canvas.width = 1024;
    canvas.height = 576;
    const ctx = canvas.getContext('2d');

    const bgGrad = ctx.createRadialGradient(512, 288, 60, 512, 288, 520);
    bgGrad.addColorStop(0, '#1c1917');
    bgGrad.addColorStop(1, '#090807');
    ctx.fillStyle = bgGrad;
    ctx.fillRect(0, 0, 1024, 576);

    ctx.strokeStyle = '#b58b4b';
    ctx.lineWidth = 6;
    ctx.strokeRect(18, 18, 988, 540);

    ctx.strokeStyle = 'rgba(250, 204, 21, 0.4)';
    ctx.lineWidth = 2;
    ctx.strokeRect(26, 26, 972, 524);

    ctx.fillStyle = '#facc15';
    ctx.font = 'bold 26px Georgia, serif';
    ctx.textAlign = 'center';
    ctx.fillText('FIVE METAL MASONRY', 512, 85);

    ctx.fillStyle = '#d4af37';
    ctx.font = '600 13px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    ctx.fillText('SHILPA SASTRA · STHAPATI ICONOMETRIC ARCHIVE', 512, 115);

    const texture = new THREE.CanvasTexture(canvas);
    texture.generateMipmaps = true;
    texture.minFilter = THREE.LinearMipmapLinearFilter;
    return texture;
  }

  buildTablet() {
    this.tabletGroup = new THREE.Group();

    const tabletW = 4.2;
    const tabletH = tabletW / this.options.aspectRatio; // ~2.36
    const tabletD = 0.09;

    // 1. Panchaloha Beveled Outer Frame
    const frameGeo = new THREE.BoxGeometry(tabletW + 0.12, tabletH + 0.12, tabletD);
    this.frameMaterial = new THREE.MeshStandardMaterial({
      color: 0xc29b38,
      roughness: 0.28,
      metalness: 0.88
    });
    const frameMesh = new THREE.Mesh(frameGeo, this.frameMaterial);
    this.tabletGroup.add(frameMesh);

    // Texture loader with max anisotropy
    const textureLoader = new THREE.TextureLoader();
    const maxAnisotropy = this.renderer ? this.renderer.capabilities.getMaxAnisotropy() : 8;

    // 2. Front Face: High-Res Shilpa Shastra Iconography Artwork
    const frontGeo = new THREE.PlaneGeometry(tabletW, tabletH);
    const frontTexture = textureLoader.load(
      this.options.imageUrl || 'assets/shilpa_shastra_iconography.png',
      (tex) => {
        tex.generateMipmaps = true;
        tex.minFilter = THREE.LinearMipmapLinearFilter;
        tex.magFilter = THREE.LinearFilter;
        tex.anisotropy = maxAnisotropy;
        tex.encoding = THREE.sRGBEncoding;
        tex.needsUpdate = true;
        if (this.renderer && this.scene && this.camera) {
          this.renderer.render(this.scene, this.camera);
        }
      },
      undefined,
      (err) => {
        console.warn('[Hero3D] Front image load error:', err);
      }
    );
    frontTexture.generateMipmaps = true;
    frontTexture.minFilter = THREE.LinearMipmapLinearFilter;
    frontTexture.magFilter = THREE.LinearFilter;
    frontTexture.anisotropy = maxAnisotropy;
    frontTexture.encoding = THREE.sRGBEncoding;

    // IMPORTANT: metalness: 0.0 prevents specular washout of dark canvas!
    this.frontMaterial = new THREE.MeshStandardMaterial({
      map: frontTexture,
      roughness: 0.35,
      metalness: 0.0
    });

    const frontMesh = new THREE.Mesh(frontGeo, this.frontMaterial);
    frontMesh.position.z = tabletD / 2 + 0.005;
    this.tabletGroup.add(frontMesh);

    // 3. Back Face: Official Five Metal Masonry 5MM Insignia & Reverse Tablet
    const backGeo = new THREE.PlaneGeometry(tabletW, tabletH);
    const backTexture = textureLoader.load(
      this.options.reverseUrl || 'assets/shilpa_shastra_reverse.png',
      (tex) => {
        tex.generateMipmaps = true;
        tex.minFilter = THREE.LinearMipmapLinearFilter;
        tex.magFilter = THREE.LinearFilter;
        tex.anisotropy = maxAnisotropy;
        tex.encoding = THREE.sRGBEncoding;
        tex.needsUpdate = true;
        if (this.renderer && this.scene && this.camera) {
          this.renderer.render(this.scene, this.camera);
        }
      },
      undefined,
      (err) => {
        console.warn('[Hero3D] Reverse texture load error, falling back to grid:', err);
        if (this.backMaterial) {
          this.backMaterial.map = this.createSthapatiGridTexture();
          this.backMaterial.needsUpdate = true;
        }
      }
    );
    backTexture.generateMipmaps = true;
    backTexture.minFilter = THREE.LinearMipmapLinearFilter;
    backTexture.magFilter = THREE.LinearFilter;
    backTexture.anisotropy = maxAnisotropy;
    backTexture.encoding = THREE.sRGBEncoding;

    this.backMaterial = new THREE.MeshStandardMaterial({
      map: backTexture,
      roughness: 0.35,
      metalness: 0.0
    });

    const backMesh = new THREE.Mesh(backGeo, this.backMaterial);
    backMesh.position.z = - (tabletD / 2 + 0.005);
    backMesh.rotation.y = Math.PI; // Face outwards on back
    this.tabletGroup.add(backMesh);

    this.scene.add(this.tabletGroup);
  }

  buildHalos() {
    this.haloGroup = new THREE.Group();

    // Outer Orbit Ring (Dharmachakra Inclined)
    const halo1Geo = new THREE.TorusGeometry(2.75, 0.018, 16, 96);
    this.haloMaterial1 = new THREE.MeshStandardMaterial({
      color: 0xd4af37,
      metalness: 0.92,
      roughness: 0.22,
      transparent: true,
      opacity: 0.55
    });
    this.haloMesh1 = new THREE.Mesh(halo1Geo, this.haloMaterial1);
    this.haloMesh1.rotation.x = Math.PI / 4;
    this.haloGroup.add(this.haloMesh1);

    // Inner Counter-Rotating Ring
    const halo2Geo = new THREE.TorusGeometry(2.55, 0.012, 16, 80);
    this.haloMaterial2 = new THREE.MeshStandardMaterial({
      color: 0xfacc15,
      metalness: 0.95,
      roughness: 0.18,
      transparent: true,
      opacity: 0.4
    });
    this.haloMesh2 = new THREE.Mesh(halo2Geo, this.haloMaterial2);
    this.haloMesh2.rotation.y = Math.PI / 3;
    this.haloMesh2.rotation.z = Math.PI / 6;
    this.haloGroup.add(this.haloMesh2);

    this.scene.add(this.haloGroup);
  }

  buildParticles() {
    const count = 90;
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(count * 3);
    const scales = new Float32Array(count);

    for (let i = 0; i < count; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 8.5;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 6.5;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 4.5;
      scales[i] = Math.random();
    }

    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

    this.particleMaterial = new THREE.PointsMaterial({
      color: 0xfacc15,
      size: 0.045,
      transparent: true,
      opacity: 0.55,
      blending: THREE.AdditiveBlending
    });

    this.particles = new THREE.Points(geometry, this.particleMaterial);
    this.scene.add(this.particles);
  }

  syncTheme(theme) {
    const isDark = theme === 'dark';

    if (isDark) {
      if (this.ambientLight) {
        this.ambientLight.color.setHex(0xfff8ee);
        this.ambientLight.intensity = 0.35;
      }
      if (this.keyLight) {
        this.keyLight.color.setHex(0xfff5ea);
        this.keyLight.intensity = 1.05;
      }
      if (this.shivaFill) {
        this.shivaFill.color.setHex(0x38bdf8);
        this.shivaFill.intensity = 0.38;
      }
      if (this.ganeshaFill) {
        this.ganeshaFill.color.setHex(0xf59e0b);
        this.ganeshaFill.intensity = 0.48;
      }
      if (this.rimLight) {
        this.rimLight.color.setHex(0xc29b38);
        this.rimLight.intensity = 0.60;
      }
      if (this.particleMaterial) {
        this.particleMaterial.color.setHex(0xfacc15);
        this.particleMaterial.opacity = 0.55;
      }
      if (this.frameMaterial) {
        this.frameMaterial.color.setHex(0xd4af37);
        this.frameMaterial.metalness = 0.90;
        this.frameMaterial.roughness = 0.25;
      }
    } else {
      if (this.ambientLight) {
        this.ambientLight.color.setHex(0xfff8ee);
        this.ambientLight.intensity = 0.45;
      }
      if (this.keyLight) {
        this.keyLight.color.setHex(0xfff5ea);
        this.keyLight.intensity = 1.15;
      }
      if (this.shivaFill) {
        this.shivaFill.color.setHex(0x0ea5e9);
        this.shivaFill.intensity = 0.35;
      }
      if (this.ganeshaFill) {
        this.ganeshaFill.color.setHex(0xd97706);
        this.ganeshaFill.intensity = 0.45;
      }
      if (this.rimLight) {
        this.rimLight.color.setHex(0xb58b4b);
        this.rimLight.intensity = 0.55;
      }
      if (this.particleMaterial) {
        this.particleMaterial.color.setHex(0xb58b4b);
        this.particleMaterial.opacity = 0.40;
      }
      if (this.frameMaterial) {
        this.frameMaterial.color.setHex(0xc29b38);
        this.frameMaterial.metalness = 0.88;
        this.frameMaterial.roughness = 0.28;
      }
    }
  }

  bindEvents() {
    const el = this.renderer.domElement;

    // Mouse Drag Rotation
    el.addEventListener('mousedown', (e) => {
      this.isDragging = true;
      this.previousMousePosition = { x: e.clientX, y: e.clientY };
    });

    window.addEventListener('mousemove', (e) => {
      // Parallax Tilt when moving anywhere in hero
      const rect = this.container.getBoundingClientRect();
      const xNorm = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      const yNorm = ((e.clientY - rect.top) / rect.height) * 2 - 1;

      if (xNorm >= -1.5 && xNorm <= 1.5 && yNorm >= -1.5 && yNorm <= 1.5) {
        this.targetParallaxX = xNorm * 0.22;
        this.targetParallaxY = - yNorm * 0.16;
      }

      if (!this.isDragging) return;

      const deltaX = e.clientX - this.previousMousePosition.x;
      const deltaY = e.clientY - this.previousMousePosition.y;

      this.targetRotationY += deltaX * 0.008;
      this.targetRotationX += deltaY * 0.008;

      // Clamp vertical tilt to prevent disorientation
      this.targetRotationX = Math.max(-0.65, Math.min(0.65, this.targetRotationX));

      this.previousMousePosition = { x: e.clientX, y: e.clientY };
    });

    window.addEventListener('mouseup', () => {
      this.isDragging = false;
    });

    // Touch Support
    el.addEventListener('touchstart', (e) => {
      if (e.touches.length === 1) {
        this.isDragging = true;
        this.previousMousePosition = { x: e.touches[0].clientX, y: e.touches[0].clientY };
      }
    }, { passive: true });

    window.addEventListener('touchmove', (e) => {
      if (!this.isDragging || e.touches.length !== 1) return;
      const deltaX = e.touches[0].clientX - this.previousMousePosition.x;
      const deltaY = e.touches[0].clientY - this.previousMousePosition.y;

      this.targetRotationY += deltaX * 0.009;
      this.targetRotationX += deltaY * 0.009;
      this.targetRotationX = Math.max(-0.65, Math.min(0.65, this.targetRotationX));

      this.previousMousePosition = { x: e.touches[0].clientX, y: e.touches[0].clientY };
    }, { passive: true });

    window.addEventListener('touchend', () => {
      this.isDragging = false;
    });

    // Double-click to gently reset orientation
    el.addEventListener('dblclick', () => {
      this.targetRotationX = 0;
      this.targetRotationY = 0;
    });

    // Resize Observer
    if (window.ResizeObserver) {
      this.resizeObserver = new ResizeObserver(() => this.onResize());
      this.resizeObserver.observe(this.container);
    } else {
      window.addEventListener('resize', () => this.onResize());
    }

    // Theme Mutation Observer
    this.themeObserver = new MutationObserver((mutations) => {
      mutations.forEach((m) => {
        if (m.type === 'attributes' && m.attributeName === 'data-theme') {
          const theme = document.documentElement.getAttribute('data-theme') || 'light';
          this.syncTheme(theme);
        }
      });
    });
    this.themeObserver.observe(document.documentElement, { attributes: true });
  }

  onResize() {
    if (!this.container || !this.renderer || !this.camera) return;
    const width = this.container.clientWidth;
    const height = this.container.clientHeight;
    if (width === 0 || height === 0) return;

    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height);
  }

  animate() {
    this.animationFrameId = requestAnimationFrame(() => this.animate());

    const elapsedTime = this.clock.getElapsedTime();

    // Harmonic Idle Float (Bobbing and slight yaw precession)
    const floatY = Math.sin(elapsedTime * 1.3) * 0.07;
    const floatRotY = Math.sin(elapsedTime * 0.65) * 0.04;
    const floatRotX = Math.cos(elapsedTime * 0.85) * 0.025;

    // Smooth Lerp for rotations and parallax
    this.currentRotationY += (this.targetRotationY - this.currentRotationY) * 0.09;
    this.currentRotationX += (this.targetRotationX - this.currentRotationX) * 0.09;
    this.parallaxX += (this.targetParallaxX - this.parallaxX) * 0.06;
    this.parallaxY += (this.targetParallaxY - this.parallaxY) * 0.06;

    if (this.tabletGroup) {
      this.tabletGroup.position.y = floatY;
      this.tabletGroup.rotation.y = this.currentRotationY + this.parallaxX + floatRotY;
      this.tabletGroup.rotation.x = this.currentRotationX + this.parallaxY + floatRotX;
    }

    // Orbit Halos Rotation
    if (this.haloMesh1) {
      this.haloMesh1.rotation.z += 0.003;
      this.haloMesh1.rotation.y += 0.002;
    }
    if (this.haloMesh2) {
      this.haloMesh2.rotation.x -= 0.004;
      this.haloMesh2.rotation.z -= 0.003;
    }

    // Slowly Rotate Celestial Dust Field
    if (this.particles) {
      this.particles.rotation.y += 0.001;
      this.particles.rotation.x = Math.sin(elapsedTime * 0.3) * 0.05;
    }

    this.renderer.render(this.scene, this.camera);
  }

  destroy() {
    if (this.animationFrameId) cancelAnimationFrame(this.animationFrameId);
    if (this.resizeObserver) this.resizeObserver.disconnect();
    if (this.themeObserver) this.themeObserver.disconnect();
    if (this.renderer && this.renderer.domElement) {
      this.renderer.domElement.remove();
    }
  }
}

// Global initialization helper
window.FMMHeroIconography3D = FMMHeroIconography3D;
