function test(): integer {
  let x: integer = 10;
  return x;
  let y: integer = 20;   // <- Código muerto, nunca se ejecuta
}

function loop() {
  while (true) {
    break;
    let z: integer = 30; // <- Código muerto, después de break
  }
}
