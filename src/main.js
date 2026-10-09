import './style.css';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

const $ = (selector) => document.querySelector(selector);
const viewport = $('#viewport');
let renderer;
try {
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, preserveDrawingBuffer: true });
} catch (error) {
  $('#load-progress').textContent = 'WebGL is unavailable. Download the GLB to open it in a 3D editor.';
  $('.loader-ring').hidden = true;
  throw error;
}
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.75));
renderer.setClearColor(0x111514);
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.domElement.tabIndex = 0;
renderer.domElement.setAttribute('aria-label', 'Orbit the mech with mouse drag or arrow keys; zoom with the scroll wheel');
viewport.append(renderer.domElement);

const scene = new THREE.Scene();
let renderNeeded = true;
// The model and light rig are static. Reuse the shadow map until an assembly
// moves, and redraw only on interaction instead of consuming the GPU at idle.
renderer.shadowMap.autoUpdate = false;
renderer.shadowMap.needsUpdate = true;
scene.fog = new THREE.FogExp2(0x111514, .024);
const camera = new THREE.PerspectiveCamera(34, 1, .1, 100);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = .065;
controls.minDistance = 3;
controls.maxDistance = 32;
controls.maxPolarAngle = Math.PI * .49;
controls.autoRotateSpeed = .65;
controls.listenToKeyEvents(renderer.domElement);

const pmrem = new THREE.PMREMGenerator(renderer);
const room = new RoomEnvironment();
const envTarget = pmrem.fromScene(room, .04);
scene.environment = envTarget.texture;
scene.environmentIntensity = .72;
room.dispose();
pmrem.dispose();

const key = new THREE.DirectionalLight(0xffe8ce, 4.3);
key.position.set(4, 10, 6);
key.castShadow = true;
key.shadow.mapSize.set(2048, 2048);
key.shadow.camera.left = -7;
key.shadow.camera.right = 7;
key.shadow.camera.top = 10;
key.shadow.camera.bottom = -5;
key.shadow.camera.near = .5;
key.shadow.camera.far = 35;
key.shadow.bias = -.0003;
key.shadow.normalBias = .035;
key.shadow.radius = 3;
key.target.position.set(0, 3.5, 0);
scene.add(key, key.target);
const fill = new THREE.DirectionalLight(0xaacbdf, 2.1);
fill.position.set(-6, 5, 2);
scene.add(fill);
const rim = new THREE.DirectionalLight(0xf8ce93, 3.6);
rim.position.set(3, 7, -5);
scene.add(rim);
scene.add(new THREE.HemisphereLight(0xc2d0d0, 0x21221d, .8));

const ground = new THREE.Mesh(new THREE.PlaneGeometry(160, 160), new THREE.MeshStandardMaterial({color:0x191d19, roughness:.85, metalness:.18}));
ground.rotation.x = -Math.PI / 2;
ground.position.y = .015;
ground.receiveShadow = true;
scene.add(ground);

const grid = new THREE.GridHelper(32, 32, 0x354030, 0x252d23);
grid.position.y = .018;
grid.material.transparent = true;
grid.material.opacity = .25;
scene.add(grid);
const stageRing = new THREE.Mesh(new THREE.RingGeometry(3.6, 3.615, 100), new THREE.MeshBasicMaterial({color:0x6b795d, transparent:true, opacity:.28, side:THREE.DoubleSide}));
stageRing.rotation.x = -Math.PI / 2;
stageRing.position.y = .02;
scene.add(stageRing);

// A soft, radial contact shadow complements the directional shadow at the soles.
const shadowCanvas = document.createElement('canvas');
shadowCanvas.width = shadowCanvas.height = 256;
const ctx = shadowCanvas.getContext('2d');
const gradient = ctx.createRadialGradient(128,128,12,128,128,125);
gradient.addColorStop(0,'rgba(0,0,0,.65)');
gradient.addColorStop(.4,'rgba(0,0,0,.3)');
gradient.addColorStop(1,'rgba(0,0,0,0)');
ctx.fillStyle = gradient;
ctx.fillRect(0,0,256,256);
const contact = new THREE.Mesh(new THREE.PlaneGeometry(7,5), new THREE.MeshBasicMaterial({map:new THREE.CanvasTexture(shadowCanvas),transparent:true,depthWrite:false}));
contact.rotation.x = -Math.PI/2;
contact.position.y = .027;
scene.add(contact);

const mech = new THREE.Group();
scene.add(mech);
const materials = new Map();
const assemblies = [];
let ready = false;
let exploded = 0;
let wireframe = false;
let animation;

function notify(message) {
  $('#toast').textContent = message;
  $('#toast').classList.add('visible');
  clearTimeout(notify.timer);
  notify.timer = setTimeout(() => $('#toast').classList.remove('visible'), 2600);
}

// Batch by assembly and material: keep the editable source model detailed,
// while rendering hundreds of components in only a few dozen draw calls.
function prepareModel(source) {
  source.updateMatrixWorld(true);
  const buckets = new Map();
  source.traverse(object => {
    if (!object.isMesh) return;
    let parent = object.parent;
    let name = 'Auxiliary systems';
    while (parent && parent !== source) {
      if (/^(Leg|Arm|Head|Torso|Backpack)[_ ]·|^Pelvis[_ ]&|^Auxiliary[_ ]sensor/.test(parent.name)) {name = parent.name; break;}
      parent = parent.parent;
    }
    const geometry = object.geometry.clone().applyMatrix4(object.matrixWorld);
    const raw = geometry.index ? geometry.toNonIndexed() : geometry;
    if (!raw.attributes.normal) raw.computeVertexNormals();
    if (!raw.attributes.uv) raw.setAttribute('uv',new THREE.BufferAttribute(new Float32Array(raw.attributes.position.count * 2),2));
    for (const key of Object.keys(raw.attributes)) if (!['position','normal','uv'].includes(key)) raw.deleteAttribute(key);
    const array = Array.isArray(object.material) ? object.material : [object.material];
    const ranges = geometry.groups.length ? geometry.groups : [{ start:0,count:raw.attributes.position.count,materialIndex:0 }];
    for (const range of ranges) {
      const material = array[range.materialIndex];
      if (!material) continue;
      const id = name + '|' + material.uuid;
      if (!buckets.has(id)) buckets.set(id,{name,material,geometries:[]});
      const piece = new THREE.BufferGeometry();
      for (const [key, attr] of Object.entries(raw.attributes)) {
        piece.setAttribute(key,new THREE.BufferAttribute(attr.array.slice(range.start * attr.itemSize,(range.start+range.count)*attr.itemSize),attr.itemSize));
      }
      buckets.get(id).geometries.push(piece);
      if (!materials.has(material.uuid)) materials.set(material.uuid,{material,roughness:material.roughness,color:material.color.clone(),map:material.map,emissive:material.emissive.clone()});
    }
    raw.dispose();
    if (raw !== geometry) geometry.dispose();
  });
  const groups = new Map();
  for (const {name,material,geometries} of buckets.values()) {
    if (!groups.has(name)) { const group=new THREE.Group();group.name=name;groups.set(name,group);mech.add(group); }
    const merged = mergeGeometries(geometries);
    const mesh = new THREE.Mesh(merged,material);
    mesh.castShadow = mesh.receiveShadow = true;
    groups.get(name).add(mesh);
    geometries.forEach(g=>g.dispose());
    for (const prop of ['map','roughnessMap','metalnessMap','normalMap']) if (material[prop]) material[prop].anisotropy = Math.min(renderer.capabilities.getMaxAnisotropy(),8);
  }
  for (const group of groups.values()) {
    const center = new THREE.Box3().setFromObject(group).getCenter(new THREE.Vector3());
    const direction = center.sub(new THREE.Vector3(0,4,0));
    // Keep the feet above the floor while separating the lower chassis.
    if (group.name.startsWith('Leg')) direction.y = 0;
    direction.normalize().multiplyScalar(1.7);
    assemblies.push({group,direction});
  }
  source.traverse(o=> {if(o.isMesh)o.geometry.dispose();});
}

new GLTFLoader().load('/models/nomad-mk07.glb', gltf => {
  prepareModel(gltf.scene);
  ready = true;
  renderNeeded = true;
  renderer.shadowMap.needsUpdate = true;
  $('#loading').hidden = true;
  $('#render-status').textContent = 'MODEL ONLINE';
  viewport.dataset.ready = 'true';
}, event => {
  if (event.total) $('#load-progress').textContent = `${Math.round(event.loaded / event.total * 100)}% · Loading model & textures`;
}, error => {
  console.error(error);
  $('#load-progress').textContent = 'Model could not load. Refresh to try again.';
  $('.loader-ring').hidden = true;
  $('#render-status').textContent = 'LOAD FAILED';
});

fetch('/models/manifest.json').then(r=>r.json()).then(stats=>{
  $('#mesh-count').textContent = stats.mesh_count;
  $('#triangle-count').textContent = stats.triangles.toLocaleString();
}).catch(error=>console.error('Manifest unavailable',error));

const cameraViews = {
  hero: {position:[10.8,7.3,16.8], target:[0,3.9,0]},
  front: {position:[0,5.8,19.2], target:[0,3.9,0]},
  rear: {position:[-10,7.2,-17], target:[0,3.9,0]},
  detail: {position:[3.3,7.8,5.9], target:[0,6.5,0]},
};
let currentView='hero';
function setCamera(view, immediate=false) {
  currentView = view;
  const state = cameraViews[view];
  const pos = new THREE.Vector3(...state.position);
  const target = new THREE.Vector3(...state.target);
  if (window.innerWidth <= 760 && view !== 'detail') {pos.multiplyScalar(1.22);target.y=3.6;}
  if (immediate || matchMedia('(prefers-reduced-motion: reduce)').matches) {camera.position.copy(pos);controls.target.copy(target);controls.update();}
  else animation={start:performance.now(),from:camera.position.clone(),to:pos,fromTarget:controls.target.clone(),toTarget:target};
  document.querySelectorAll('[data-camera]').forEach(b=>b.classList.toggle('selected',b.dataset.camera===view));
}
document.querySelectorAll('[data-camera]').forEach(button=>button.addEventListener('click',()=>setCamera(button.dataset.camera)));

function resize() {
  const width=viewport.clientWidth,height=viewport.clientHeight;
  renderer.setSize(width,height);
  renderNeeded = true;
  camera.aspect=width/height;
  camera.updateProjectionMatrix();
  // Shift the optical center slightly right to balance the editorial sidebar.
  if (width > 760) camera.setViewOffset(width,height,-width*.025,0,width,height);
  else camera.clearViewOffset();
}
new ResizeObserver(resize).observe(viewport);
setCamera('hero',true);
resize();

document.querySelectorAll('[data-tab]').forEach(button=>button.addEventListener('click',()=>{
  document.querySelectorAll('[data-tab]').forEach(b=>b.classList.toggle('active',b===button));
  const tab=button.dataset.tab;
  document.querySelectorAll('.control-panel').forEach(panel=>panel.hidden=panel.id!==`${tab}-panel`);
  $('#panel-title').textContent={overview:'SCENE CONTROLS',materials:'MATERIAL LAB',specs:'TECHNICAL BLUEPRINT'}[tab];
  $('.panel-index').textContent={overview:'/ 01',materials:'/ 02',specs:'/ 03'}[tab];
  $('#mobile-panel-label').textContent={overview:'Scene controls',materials:'Material lab',specs:'Blueprint'}[tab];
  if (window.innerWidth <= 760) {
    $('main').classList.add('mobile-panel-open');
    $('#panel-toggle').setAttribute('aria-expanded','true');
  }
}));
$('#panel-toggle').addEventListener('click',()=>{
  const open=$('main').classList.toggle('mobile-panel-open');
  $('#panel-toggle').setAttribute('aria-expanded',String(open));
});

function setExplode(value) {
  exploded = value / 100;
  $('#explode-value').textContent = `${value}%`;
  for (const {group,direction} of assemblies) group.position.copy(direction).multiplyScalar(exploded);
  renderer.shadowMap.needsUpdate = true;
}
$('#explode').addEventListener('input',event=>setExplode(Number(event.target.value)));

const lighting = {
  studio:{key:0xffe8ce,fill:0xaacbdf,rim:0xf8ce93,keyPower:4.3,fillPower:2.1,rimPower:3.6,env:.72,bg:0x111514},
  hangar:{key:0xd5e9ef,fill:0x9aeadf,rim:0xc9d2ef,keyPower:3.3,fillPower:2.0,rimPower:5,env:.5,bg:0x101a1c},
  dusk:{key:0xffb069,fill:0x7195d8,rim:0xff7846,keyPower:2.7,fillPower:1.3,rimPower:5,env:.32,bg:0x1b1516},
};
function setLight(name) {
  const s=lighting[name];
  key.color.setHex(s.key);fill.color.setHex(s.fill);rim.color.setHex(s.rim);
  key.intensity=s.keyPower;fill.intensity=s.fillPower;rim.intensity=s.rimPower;
  scene.environmentIntensity=s.env;
  renderer.setClearColor(s.bg);scene.fog.color.setHex(s.bg);
  document.querySelectorAll('[data-light]').forEach(b=>b.classList.toggle('selected',b.dataset.light===name));
}
document.querySelectorAll('[data-light]').forEach(button=>button.addEventListener('click',()=>setLight(button.dataset.light)));

const finishes={field:{color:0xffffff,label:'Field green'},arctic:{color:0xdde8f0,label:'Arctic white'},desert:{color:0xd5b789,label:'Desert sand'},stealth:{color:0x596773,label:'Stealth graphite'}};
const finishTextures = {};
for (const name of ['arctic','desert','stealth']) {
  const texture = new THREE.TextureLoader().load(`/textures/ceramic-${name}.jpg`,()=>{renderNeeded=true;});
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.flipY = false;
  texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
  texture.anisotropy = Math.min(renderer.capabilities.getMaxAnisotropy(),8);
  finishTextures[name] = texture;
}
function setFinish(name) {
  const finish=finishes[name];
  for (const {material,map} of materials.values()) if (material.name.startsWith('01')) {
    material.map = name === 'field' ? map : finishTextures[name];
    material.color.setHex(0xffffff);
    material.needsUpdate = true;
  }
  $('#finish-label').textContent=finish.label;
  document.querySelectorAll('[data-finish]').forEach(b=>b.classList.toggle('selected',b.dataset.finish===name));
}
document.querySelectorAll('[data-finish]').forEach(button=>button.addEventListener('click',()=>setFinish(button.dataset.finish)));
$('#roughness').addEventListener('input',event=>{
  const value=Number(event.target.value);
  $('#roughness-value').textContent=`${value}%`;
  for (const {material,roughness} of materials.values()) if (!material.name.startsWith('05')) material.roughness=roughness*value/100;
});
$('#exposure').addEventListener('input',event=>{
  renderer.toneMappingExposure=Number(event.target.value)/100;
  $('#exposure-value').textContent=renderer.toneMappingExposure.toFixed(1);
});

function setWireframe(value) {
  wireframe=value;
  for (const {material} of materials.values()) material.wireframe=value;
  $('#solid').classList.toggle('selected',!value);
  $('#wireframe').classList.toggle('selected',value);
}
$('#solid').addEventListener('click',()=>setWireframe(false));
$('#wireframe').addEventListener('click',()=>setWireframe(true));
$('#rotate').addEventListener('click',()=>{
  controls.autoRotate=!controls.autoRotate;
  $('#rotate').classList.toggle('selected',controls.autoRotate);
  $('#rotate').setAttribute('aria-pressed',String(controls.autoRotate));
});
$('#reset').addEventListener('click',()=>{
  controls.autoRotate=false;
  $('#rotate').classList.remove('selected');$('#rotate').setAttribute('aria-pressed','false');
  setWireframe(false);setLight('studio');setFinish('field');
  $('#explode').value=0;setExplode(0);
  $('#roughness').value=100;$('#roughness-value').textContent='100%';
  for (const {material,roughness} of materials.values()) material.roughness=roughness;
  $('#exposure').value=100;$('#exposure-value').textContent='1.0';renderer.toneMappingExposure=1;
  setCamera('hero');notify('Scene reset to studio defaults');
});
$('#capture').addEventListener('click',()=>{
  if (!ready) {notify('The model is still loading');return;}
  renderer.render(scene,camera);
  renderer.domElement.toBlob(blob=>{
    if(!blob) {notify('Screenshot could not be saved');return;}
    const url=URL.createObjectURL(blob);
    const link=document.createElement('a');link.download='nomad-mk07.png';link.href=url;link.click();
    setTimeout(()=>URL.revokeObjectURL(url),3000);
    notify('Render saved as nomad-mk07.png');
  },'image/png');
});
controls.addEventListener('start',()=>{animation=null;});
controls.addEventListener('change',()=>{renderNeeded=true;});
for (const event of ['click','input']) document.addEventListener(event,()=>{renderNeeded=true;});
renderer.setAnimationLoop(time=>{
  if (animation) {
    const t=Math.min(1,(time-animation.start)/850);
    const ease=t*t*(3-2*t);
    camera.position.lerpVectors(animation.from,animation.to,ease);
    controls.target.lerpVectors(animation.fromTarget,animation.toTarget,ease);
    if(t===1)animation=null;
  }
  controls.update();
  if (renderNeeded) {
    renderer.render(scene,camera);
    renderNeeded = false;
  }
});

// Read-only diagnostics for smoke checks and graphics troubleshooting.
window.nomadDiagnostics=()=>({ready,assemblies:assemblies.length,materials:materials.size,drawCalls:renderer.info.render.calls,triangles:renderer.info.render.triangles,exploded,wireframe,view:currentView});
