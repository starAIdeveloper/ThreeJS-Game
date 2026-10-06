import {world,THREE} from './scene.js';
const {scene,animate}=world();const objects=[];
const sun=new THREE.Mesh(new THREE.SphereGeometry(.8,32,24),new THREE.MeshBasicMaterial({color:'#ffbf57'}));sun.userData.label='Sun';scene.add(sun);
const data=[['Mercury',1.5,.12,0xaaa49a,1.8],['Venus',2.1,.2,0xe5bb83,1.2],['Earth',2.9,.23,0x559ed6,.9],['Mars',3.7,.18,0xdb7558,.7],['Jupiter',5,.5,0xc4a07f,.35]];
for(const [name,r,size,color,speed] of data){const mesh=new THREE.Mesh(new THREE.SphereGeometry(size,24,16),new THREE.MeshStandardMaterial({color}));mesh.userData.label=name+' | Illustrative orbit radius '+r;scene.add(mesh);objects.push({mesh,r,speed,angle:0});const pts=[];for(let i=0;i<=128;i++){const a=i/128*Math.PI*2;pts.push(new THREE.Vector3(Math.cos(a)*r,0,Math.sin(a)*r));}scene.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts),new THREE.LineBasicMaterial({color:0x394f65})));}
animate(dt=>{for(const o of objects){if(!document.querySelector('#pause').checked)o.angle+=dt*o.speed*Number(document.querySelector('#speed').value);o.mesh.position.set(Math.cos(o.angle)*o.r,0,Math.sin(o.angle)*o.r);}});
