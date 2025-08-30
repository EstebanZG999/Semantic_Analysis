// Error 1: asignación incompatible (integer ← string)
let x: integer = "texto";

// Error 2: redeclaración en el mismo scope
let y: boolean = true;
let y: integer = 5;

// Error 3: condición del if no es booleana
if (123) {
  print("Esto no debería compilar");
}

// Error 4: llamada de función con parámetros incorrectos
function cuadrado(n: integer): integer {
  return n * n;
}
let z: integer = cuadrado("hola");  // pasa string en lugar de int

// Error 5: función retorna string pero tipada como integer
function malo(): integer {
  return "soy un string";
}
