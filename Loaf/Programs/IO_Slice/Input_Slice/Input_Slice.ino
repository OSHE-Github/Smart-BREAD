#include <SPI.h>
#include <ACAN2515.h>
#include "MCP3208.h"

//CAN Configuration
#define CANCS   1
#define CANINT  4
#define canTXID 0x100
#define canRXID 0x1A3
#define OSCFREQ 16000000UL // 16 MHz
#define CANSPEED 500000 // 500 kbps

ACAN2515 can(CANCS, SPI, CANINT);
CANMessage txMSG;
CANMessage rxMSG;

//Can Frame Vars
uint8_t dataLen = 8;
int16_t canID = 0;

//Decoded value vars
uint8_t modeIO = 0;
uint8_t modeFlag = 0 ;
uint8_t pinNum = 0;
uint8_t res1 = 0;
uint8_t res2 = 0;
int16_t bulkDigi = 0;
uint8_t pwmDuty = 0;
int32_t dataSeg = 0;

//Counters
uint32_t lastMessageTime = 0;
uint32_t messageCounter = 0;

//ADC Configuration
#define ADCCS 7
#define numAnalog 8
MCP3208 externADC;

//Digital pin setup
#define numDigital 8
const uint8_t digiPins[numDigital] {26, 22, 21, 20, 19, 18, 17, 16}; //DIO0, DIO1, DIO2, DIO3, DIO4, DIO5, DIO6, DIO7

//Runtime Flags
#define canDebug false

//Decode the CAN message recieved into the required fields. Refer to I/O Slice CAN message spec for details.
void canDecode(uint8_t canData[]){
  char byte = canData[0];
  modeIO = (byte & 0b11000000) >> 6;
  modeFlag =  (byte & 0b00110000) >> 4;
  pinNum =  byte & 0b00001111;

  //Reserved data reading
  //res1 = canMsg.data[1];

  //PWM Duty cycle reading
  if(modeFlag == 2){pwmDuty = canData[4];}

  //Bulk Digital pin decoding
  if(modeFlag == 3){
    bulkDigi = canData[2];
    bulkDigi = (bulkDigi << 8) + canData[3];
  }

  //Data Segment Decoding
  dataSeg = canData[5];
  dataSeg = (dataSeg << 8) + canData[6];
  dataSeg = (dataSeg << 8) + canData[7];
}

//Encode a new message and return the encoded message
void canEncode(uint16_t bulkDigi, uint8_t pwmDuty, uint32_t dataSeg){

  txMSG.id = canTXID;
  txMSG.len = dataLen;

  //Info Byte encoding
  txMSG.data[0] = 0b10000000;
  txMSG.data[0] = txMSG.data[0] + pinNum + (modeFlag << 4);

  //Reserved bits encoding
  txMSG.data[1] = 0; txMSG.data[4] = 0;

  //Bulk digital data encoding
  txMSG.data[2] = char(bulkDigi >> 8);
  txMSG.data[3] = char(bulkDigi & 0b0000000011111111);

  //Data segment encoding
  txMSG.data[5] = char(dataSeg >> 16);
  txMSG.data[6] = char(dataSeg >> 8) & 0b000000000000000011111111;
  txMSG.data[7] = char(dataSeg & 0b000000000000000011111111);

  //Encode PWM duty cycle
  txMSG.data[4] = pwmDuty;
}

uint16_t readAnalog(uint8_t pin){
  uint16_t out = 0;
  Serial.print("Reading analog pin: "); Serial.println(digiPins[pin]);
  out = externADC.analogRead(pin);
  Serial.print(out); Serial.println(" Counts");

  float voltage = (out * 3.3) / 4095.0;
  Serial.print(voltage); Serial.println(" V");

  return out;
}

//Read specified digital pin
uint16_t readDigital(uint8_t pin){
  uint16_t out = 0;
  out = digitalRead(digiPins[pin]);
  Serial.print("Read digital pin: ");
  Serial.println(digiPins[pin]);
  Serial.println(out);
  return out;
}

//Read many digital pins
uint16_t readManyDigital(uint16_t pins){
  uint16_t out = 0;
  for(uint16_t i = 0; i < numDigital; i++){
    //Mask pins so that we can efficiently calculate if the pin is to be read or not.
    uint16_t mask = 0b0000000000000000 + (1 << i);
    uint16_t flag = pins & mask;

    //Read and add result to output.
    if(mask > 0){
      out = out + (digitalRead(digiPins[i]) << i);
    }
  }
  Serial.print("Read from all digital pins: "); Serial.println(out, BIN);
  return out;
}

void readPWM(uint8_t pin){
  //Listen for pwm signal
  unsigned long highTime = pulseIn(digiPins[pin], HIGH);
  unsigned long lowTime = pulseIn(digiPins[pin], LOW);
  float freq = 0;
  float duty = 0;

  if (highTime + lowTime > 0) {
    unsigned long period = highTime + lowTime;
    freq = 1000000.0 / period;
    duty = ((float)highTime / period) * 100.0;

    Serial.print("Freq: ");
    Serial.print(freq);
    Serial.print(" Hz | Duty Cycle: ");
    Serial.print(duty);
    Serial.println(" %");
  } else {
    Serial.println("No PWM signal present");
    freq = 0;
    duty = 0;
  }

  pwmDuty = uint8_t(255 * (duty/100.0));
  dataSeg = freq;
}

void setup() {
  //Serial monitor init
  Serial.begin(115200);
  while(!Serial){}

  //SPI Config
  SPI.setRX(0);
  SPI.setSCK(2);
  SPI.setTX(3);
  SPI.begin();

  ACAN2515Settings settings(OSCFREQ, CANSPEED);
  externADC.begin(ADCCS);
  externADC.analogReadResolution(12);

  Serial.println("Initializing MCP2515...");
  const uint32_t initErrorCode = can.begin(settings, [] { can.isr(); });

  if (initErrorCode == 0) {
    Serial.println("MCP2515 Initialized Successfully!");
  } else {
    Serial.print("Initialization failed. Error code: 0x");
    Serial.println(initErrorCode, HEX);
    while (1);
  }

  for(char i = 0; i < numDigital; i++){
    pinMode(digiPins[i], INPUT);
  }
}

void loop() {
while(true){
  //Recieve the CAN message
  if (can.available()) {
    can.receive(rxMSG);
    //Yoink ID and data size
    canID = rxMSG.id;
    dataLen = rxMSG.len;

    //Skip this frame if it isn't what we want
    if(canID != canRXID && dataLen != 8){continue;}

    //Decode the frame if it is of the expected length and ID
    canDecode(rxMSG.data);

    switch(modeFlag){
      //Analog Case
      case 0:
        dataSeg = readAnalog(pinNum);
      break;

      //Digital Case
      case 1:
        dataSeg = readDigital(pinNum);
      break;

      //Bulk Digital Case
      case 2:
        dataSeg = readManyDigital(bulkDigi);
      break;

      //PWM Case
      case 3:
        readPWM(pinNum);
      break;
    }

    canEncode(bulkDigi, pwmDuty, dataSeg);

    //Print CAN Frame
    Serial.print("Data: [");
    for(char i = 0; i < 7; i++){
      Serial.print(txMSG.data[i], BIN);
      Serial.print(", ");
    }
    Serial.print(txMSG.data[7], BIN);
    Serial.println("]");

    can.tryToSend(txMSG);
  }


}}










