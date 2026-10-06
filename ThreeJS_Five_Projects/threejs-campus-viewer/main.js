import {world,box,THREE} from './scene.js';
const {scene,camera,controls}=world();box(scene,[14,.15,12],[0,-.12,0],'#749777','Site landscape');
box(scene,[1,.04,12],[0,.01,0],'#d5cbb7','Main pedestrian spine');box(scene,[14,.04,.8],[0,.01,0],'#d5cbb7','Cross-campus path');
const groups={};for(const id of ['lodging','sports','community']){groups[id]=new THREE.Group();scene.add(groups[id]);document.querySelector('#'+id).onchange=e=>groups[id].visible=e.target.checked;}
for(let i=0;i<4;i++)box(groups.lodging,[1.5,1.1,1.5],[-4, .55,-4+i*2.5],'#d4b183','Accommodation '+(i+1));
box(groups.sports,[4,.05,2.5],[3,.04,-3],'#3b8c75','Sports court');box(groups.sports,[3,1.4,2.5],[3,.7,3],'#7897bd','Indoor sports hall');box(groups.community,[2,1.5,2],[-2, .75,3],'#c78f69','Community hub');
for(let i=0;i<8;i++){const tree=new THREE.Mesh(new THREE.ConeGeometry(.4,1.1,10),new THREE.MeshStandardMaterial({color:'#355b43'}));tree.position.set(-6+i*1.6,.55,-5.3);tree.userData.label='Landscape planting';scene.add(tree);}
document.querySelector('#top').onclick=()=>{camera.position.set(0,18,.01);controls.target.set(0,0,0);controls.update();};
