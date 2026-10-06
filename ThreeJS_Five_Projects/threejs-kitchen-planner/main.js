import {world,box,THREE,download} from './scene.js';
import {cabinetPositions} from './model.js';
const {scene}=world();box(scene,[12,.15,7],[0,-.1,0],'#c1b8a6','Floor');box(scene,[12,4,.1],[0,2,-1.3],'#e5dfd2','Back wall');
const units=new THREE.Group();scene.add(units);let config={count:5,color:'#6e9690',exploded:false};
function rebuild(){while(units.children.length){const x=units.children[0];units.remove(x);x.geometry.dispose();x.material.dispose();}cabinetPositions(config.count).forEach((x,i)=>{box(units,[.95,1.8,1.2],[x,.9,0],config.color,'Cabinet '+(i+1));box(units,[.87,1.6,.05],[x,.9,config.exploded?1.1:.63],config.color,'Door '+(i+1));box(units,[1,.12,1.3],[x,config.exploded?2.6:1.86,0],'#ede7da','Countertop');box(units,[.26,.04,.04],[x,1.4,config.exploded?1.14:.68],'#353d43','Handle');});}
rebuild();document.querySelector('#count').oninput=e=>{config.count=Number(e.target.value);rebuild();};document.querySelector('#color').oninput=e=>{config.color=e.target.value;rebuild();};document.querySelector('#explode').onchange=e=>{config.exploded=e.target.checked;rebuild();};document.querySelector('#export').onclick=()=>download(config,'kitchen-layout.json');
