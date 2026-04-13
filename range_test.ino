#include <ESP32Servo.h>

Servo servo;

int pinServo = 23;

void setup() {

  servo.attach(pinServo);

  /* =======================================
     CÓDIGO ORIGINAL COMENTADO
     =======================================
  // Movimiento inicial claro
  servo.write(180);
  delay(1500);

  servo.write(0);
  delay(1500);

  // Barrido completo
  for (int pos = 0; pos <= 180; pos++) {
    servo.write(pos);
    delay(10);
  }

  for (int pos = 180; pos >= 0; pos--) {
    servo.write(pos);
    delay(10);
  }

  // Posición final para alinear
  servo.write(90);
  ======================================= */


  // =======================================
  // NUEVO CÓDIGO: PRUEBAS ROM (5 CICLOS)
  // =======================================
  
  // Posición inicial ES 95
  servo.write(90);
  delay(1000); // Tiempo para que llegue y se estabilice en la posición inicial

  // Bucle que se repite exactamente 5 veces
  for (int i = 0; i < 5; i++) {
    
    // Mueve a 120 grados de golpe
    servo.write(120); // tope interior ojo izquierdo
    delay(1000); // Pausa para estabilizar

    // Regresa a 95 grados de golpe
    servo.write(50);
    delay(1000); // Pausa para estabilizar
    
  }
  // ojo izquierdo de 120 a 40
  // ojo derecho de 140 a 50
  servo.write(90);
  delay(1000); 

}

void loop() {
  // Vacío por ahora
}