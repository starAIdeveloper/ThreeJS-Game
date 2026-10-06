export function cabinetPositions(n){if(!Number.isInteger(n)||n<2||n>8)throw Error('Cabinet count must be 2 to 8');return Array.from({length:n},(_,i)=>i-(n-1)/2);}
