import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
export {THREE};
export function world(){
 const canvas=document.querySelector('canvas');
 let renderer;
 try {renderer=new THREE.WebGLRenderer({canvas,antialias:true});} catch(e){document.querySelector('#status').textContent='WebGL unavailable. Try a supported browser.'; throw e;}
 renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.shadowMap.enabled=true;
 const scene=new THREE.Scene();scene.background=new THREE.Color('#101a29');
 const camera=new THREE.PerspectiveCamera(45,1,.1,1000);camera.position.set(9,7,10);
 const controls=new OrbitControls(camera,canvas);controls.enableDamping=true;
 scene.add(new THREE.HemisphereLight(0xffffff,0x536077,2));
 const light=new THREE.DirectionalLight(0xffffff,3);light.position.set(8,15,6);light.castShadow=true;scene.add(light);
 function resize(){const r=canvas.getBoundingClientRect();renderer.setSize(r.width,r.height,false);camera.aspect=r.width/r.height;camera.updateProjectionMatrix();}
 new ResizeObserver(resize).observe(canvas);resize();
 let update=()=>{};let previous=performance.now();
 renderer.setAnimationLoop(now=>{const dt=Math.min((now-previous)/1000,.05);previous=now;update(dt);controls.update();renderer.render(scene,camera);});
 const ray=new THREE.Raycaster();
 canvas.addEventListener('pointerdown',e=>{const r=canvas.getBoundingClientRect();ray.setFromCamera(new THREE.Vector2((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1),camera);const hit=ray.intersectObjects(scene.children,true).find(h=>h.object.userData.label);if(hit)document.querySelector('#status').textContent=hit.object.userData.label;});
 document.querySelector('#reset').onclick=()=>{camera.position.set(9,7,10);controls.target.set(0,0,0);controls.update();};
 document.querySelector('#capture').onclick=()=>{renderer.render(scene,camera);canvas.toBlob(blob=>{if(!blob)return;const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='scene.png';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});};
 return {scene,camera,controls,animate:fn=>update=fn};
}
export function box(parent,size,pos,color,label){const m=new THREE.Mesh(new THREE.BoxGeometry(...size),new THREE.MeshStandardMaterial({color,roughness:.65}));m.position.set(...pos);m.castShadow=true;m.receiveShadow=true;m.userData.label=label;parent.add(m);return m;}
export function download(data,name){const u=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);}
