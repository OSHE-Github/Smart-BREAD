#include "AccelStepper.h"

//GPIO input mappings
const uint8_t inputs[8] = {0,1,2,3,4,5,6,7}; //Limit switches 1-4, and motor toggles 1-4 in that orders

//Motor output mappings
const uint8_t M1[3] = {8,10,9}; //Dir, Enable, Step pin asignments
const uint8_t M2[3] = {11,13,12}; //Dir, Enable, Step pin asignments
const uint8_t M3[3] = {16,18,17}; //Dir, Enable, Step pin asignments
const uint8_t M4[3] = {19,21,20}; //Dir, Enable, Step pin asignments

//Microstepping mappings
#define MS0 28
#define MS1 27
#define MS2 26

//GPIO input arrays
uint8_t limits[4] = {0,0,0,0};
uint8_t mToggles[4] = {0,0,0,0};
uint8_t motionStates[4] = {1,1,1,1};
uint8_t mTogCounts[4] = {0,0,0,0};


//Actuator settings
#define angle 22*32 //Steps
#define speed -2000.0*32
#define closeSpeed -500.0*32

//Timer storage
unsigned long timers[4] = {0,0,0,0};

// AccelStepper object declaration
AccelStepper Motor1 = AccelStepper(AccelStepper::DRIVER, M1[2], M1[0]);
AccelStepper Motor2 = AccelStepper(AccelStepper::DRIVER, M2[2], M2[0]);
AccelStepper Motor3 = AccelStepper(AccelStepper::DRIVER, M3[2], M3[0]);
AccelStepper Motor4 = AccelStepper(AccelStepper::DRIVER, M4[2], M4[0]);

AccelStepper motors[4] = {Motor1, Motor2, Motor3, Motor4};

volatile char core0Ready = 0;
volatile char core1Ready = 0;


void setup() {
  Serial.begin(115200);

  pinMode(MS0, OUTPUT);
  pinMode(MS1, OUTPUT);
  pinMode(MS2, OUTPUT);

  //Setup all GPIOS for core0 as output
  for(uint8_t i=0; i < 3; i++){
    pinMode(M1[i], OUTPUT);
    pinMode(M2[i], OUTPUT);
    pinMode(M3[i], OUTPUT);
    pinMode(M4[i], OUTPUT);
    motors[i].setPinsInverted(false, false, true); 
    motors[i].enableOutputs();
    motors[i].setMaxSpeed(speed);
    motors[i].setSpeed(speed);
    motors[i].setAcceleration(100000);
    motors[i].setCurrentPosition(0);
    motors[i].setSpeed(speed);
  }

  digitalWrite(MS0, HIGH);
  digitalWrite(MS1, HIGH);
  digitalWrite(MS2, HIGH);

  motors[0].setEnablePin(M1[1]);
  motors[1].setEnablePin(M2[1]);
  motors[2].setEnablePin(M3[1]);
  motors[3].setEnablePin(M4[1]);

  core0Ready = 1;
  while(!core1Ready){}
}

void setup1() {
  //Setup all GPIOS for core1 as input
  for(uint8_t i=0; i < 8; i++){
    pinMode(inputs[i], INPUT);
  }

  core1Ready = 1;
  while(!core0Ready){}
}

void loop() {
  motors[0].run();
  motors[1].run();
  motors[2].run();
  motors[3].run();
}

void loop1() {
  unsigned long currentTime = millis();
  //Read the values on all the pins
  //Serial.print("[");
  for(uint8_t i=0; i < 4; i++){
    limits[i] = digitalRead(inputs[i]);
    mToggles[i] = digitalRead(inputs[i+4]);
    //Serial.print(mTogCounts[i]); Serial.print(", ");

    if(mToggles[i] && mTogCounts[i] < 10){
      mTogCounts[i]++;
    }else if(mTogCounts[i] > 0 && !mToggles[i]){
      mTogCounts[i]--;
    }

    //Check for on and off signals and toggle the motor if the state changes
    if(mTogCounts[i] >= 10 & !motionStates[i]){
      Serial.print("Moving Motor "); Serial.println(i+1);
      Serial.println(mTogCounts[i]);
      motors[i].setMaxSpeed(speed);
      motors[i].setSpeed(speed);
      motors[i].moveTo(angle);
      motionStates[i] = 1;
    }else if(mTogCounts[i] == 0 & motionStates[i]){
      motors[i].setMaxSpeed(closeSpeed);
      motors[i].setSpeed(closeSpeed);
      motors[i].moveTo(-3200);
      motionStates[i] = 0;
    }

    if(limits[i] && motionStates[i] == 0){
      motors[i].setCurrentPosition(0);
    } 
  }
  //Serial.println("]");
}
