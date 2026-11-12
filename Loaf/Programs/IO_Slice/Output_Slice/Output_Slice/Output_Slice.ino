#include <SPI.h>
#include <ACAN2515.h>
#include "MCP_DAC.h"

#include "hardware/pwm.h"
#include "hardware/clocks.h"
#include "hardware/pio.h"

#define SPISPEED 10000000

//CAN Configuration
#define CANCS   1
#define CANINT  4
#define canTXID 0x105
#define canRXID 0x1A3
#define OSCFREQ 16000000 // 16 MHz
#define CANSPEED 500000 // 500 kbps

//CAN Setup
ACAN2515 can(CANCS, SPI, CANINT);
CANMessage txMSG;
CANMessage rxMSG;
CANMessage EMSG;
CANMessage workMSG;

//Can Frame Vars
uint8_t dataLen = 8;
int16_t canID = 0;

//CAN Buffers
#define bufSize 16
CANMessage txBuffer[bufSize];
CANMessage rxBuffer[bufSize];
char txFlagBuf[bufSize];
char rxFlagBuf[bufSize];

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

//Core vars
volatile char core0Setup = 0;
volatile char core1Setup = 0;
volatile char pwm_halted = 0;
volatile char STOPTHISMADNESS = 0;
char ESTOPCOUNT = 0;

//ADC Configuration
#define numAnalog 8
#define DACCS1 11
#define DACCS2 10
#define DACCS3 9
#define DACCS4 8
#define SHDNPIN 6

MCP4922 dac1(&SPI);
MCP4922 dac2(&SPI);
MCP4922 dac3(&SPI);
MCP4922 dac4(&SPI);

const uint8_t LDAC_PIN = 255;

//Digital pin setup
#define ESTOP 5
#define numDigital 8
const uint8_t digiPins[numDigital] {26, 22, 21, 20, 19, 18, 17, 16}; //DIO0, DIO1, DIO2, DIO3, DIO4, DIO5, DIO6, DIO7
uint8_t pwmsEnabled[numDigital];

//Decode the CAN message recieved into the required fields. Refer to I/O Slice CAN message spec for details.
void canDecode(uint8_t canData[]){
  char byte = canData[0];
  modeIO = (byte & 0b11000000) >> 6;
  modeFlag =  (byte & 0b00110000) >> 4;
  pinNum =  byte & 0b00001111;

  //Reserved data reading
  //res1 = canMsg.data[1];

  //PWM Duty cycle reading
  if(modeFlag == 3){pwmDuty = canData[4];}

  //Bulk Digital pin decoding
  if(modeFlag == 2){
    bulkDigi = canData[2];
    bulkDigi = (bulkDigi << 8) + canData[3];
  }

  //Data Segment Decoding
  dataSeg = canData[5];
  dataSeg = (dataSeg << 8) + canData[6];
  dataSeg = (dataSeg << 8) + canData[7];
}

//Encode a new message and return the encoded message
CANMessage canEncode(uint16_t bulkDigi, uint8_t pwmDuty, uint32_t dataSeg){
  CANMessage out;

  out.id = canTXID;
  out.len = dataLen;

  //Info Byte encoding
  out.data[0] = 0b10000000;
  out.data[0] = out.data[0] + pinNum + (modeFlag << 4);

  //Reserved bits encoding
  out.data[1] = 0; out.data[4] = 0;

  //Bulk digital data encoding
  out.data[2] = char(bulkDigi >> 8);
  out.data[3] = char(bulkDigi & 0b0000000011111111);

  //Data segment encoding
  out.data[5] = char(dataSeg >> 16);
  out.data[6] = char(dataSeg >> 8) & 0b000000000000000011111111;
  out.data[7] = char(dataSeg & 0b000000000000000011111111);

  //Encode PWM duty cycle
  out.data[4] = pwmDuty;

  return out;
}

//Read many digital pins
void writeManyDigital(uint16_t pins, uint16_t vals){
  for(uint16_t i = 0; i < numDigital; i++){
    //Mask pins so that we can efficiently calculate if the pin is to be read or not.
    uint16_t mask = 0b0000000000000000 + (1 << i);
    uint16_t flag = ((pins & mask) << (7-i)) >> 7;
    uint8_t val = ((vals & mask) << (7-i)) >> 7;
    //Read and add result to output.
    if(flag == 1){
      digitalWrite(digiPins[i], val);
      Serial.print("Wrote "); Serial.print(val); Serial.print(" to pin "); Serial.println(i);
    }
  }
  //Serial.print("Wrote from all digital pins: "); Serial.println(vals, BIN);
}

const bool USE_PIO_TONE[8] = {false, false, true, false, true, false, true, false};

void setPWM(uint8_t index, uint32_t freqHz, float dutyCycle) {
  if (index > 7) return;
  uint8_t pin = digiPins[index];

  if (freqHz == 0 || dutyCycle <= 0.0f) {
    noTone(pin);
    analogWrite(pin, 0);
    return;
  }

  if (USE_PIO_TONE[index]) {
    // Uses a dedicated PIO state machine automatically (50% duty cycle square wave)
    tone(pin, freqHz);
  } else {
    // Sets frequency for this pin's dedicated hardware slice, then writes duty cycle
    analogWriteFreq(freqHz);
    analogWrite(pin, int(255*dutyCycle));
  }
}

void writeAnalog(uint8_t pin, uint16_t val){
  switch(pin){
    case 0:
      dac3.write(val, 0);
    break;
    case 1:
      dac3.write(val, 1);
    break;
    case 2:
      dac4.write(val, 0);
    break;
    case 3:
      dac4.write(val, 1);
    break;
    case 4:
      dac1.write(val, 0);
    break;
    case 5:
      dac1.write(val, 1);
    break;
    case 6:
      dac2.write(val, 0);
    break;
    case 7:
      dac2.write(val, 1);
    break;
  }
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

  dac1.begin(DACCS1);
  dac2.begin(DACCS2);
  dac3.begin(DACCS3);
  dac4.begin(DACCS4);

  dac1.setSPIspeed(SPISPEED);
  dac2.setSPIspeed(SPISPEED);
  dac3.setSPIspeed(SPISPEED);
  dac4.setSPIspeed(SPISPEED);

  dac1.setGain(1);
  dac2.setGain(1);
  dac3.setGain(1);
  dac4.setGain(1);

  Serial.println("Initializing MCP2515...");
  const uint32_t initErrorCode = can.begin(settings, [] { can.isr(); });

  if (initErrorCode == 0) {
    Serial.println("MCP2515 Initialized Successfully!");
  } else {
    Serial.print("Initialization failed. Error code: 0x");
    Serial.println(initErrorCode, HEX);
    while (1);
  }

  //Capture to make sure the cores don't progress too out of sync
  core0Setup = 1;
  while(!core1Setup){}
}

void setup1(){
  pinMode(ESTOP, INPUT);
  pinMode(SHDNPIN, OUTPUT);

  for(char i = 0; i < numDigital; i++){
    pinMode(digiPins[i], OUTPUT);
  }
  for(char i = 0; i < numDigital; i++){
    pwmsEnabled[i] = 0;
  }

  //Format flag buffers
  for(char i = 0; i < bufSize; i++){
    txFlagBuf[i] = 0;
    rxFlagBuf[i] = 0;
  }

  EMSG.id = 0x0;
  EMSG.len = 8;

  for(char i = 0; i < 8; i++){
    EMSG.data[i] = 0b11111111;
  }

  digitalWrite(SHDNPIN, 1);

  //Capture to make sure the cores don't progress too out of sync
  core1Setup = 1;
  while(!core0Setup){}
}

void loop() {
  while(true){
  if(STOPTHISMADNESS){Serial.println("ESTOP TRIGGERED!!!!!!!!!");}
  while(STOPTHISMADNESS){
    can.tryToSend(EMSG);
    delay(100);
    if(!pwm_halted){
      for(uint8_t i; i < numDigital; i++){
        Serial.print(pwmsEnabled[i]);
        if(pwmsEnabled[i]){
          Serial.print("Pin "); Serial.print(i); Serial.println(" was enabled!");
          setPWM(i, 500, 0.0);
          }
      }
      pwm_halted = 1;
    }
  }
  
  //Recieve the CAN message
  if (can.available()) {
    can.receive(rxMSG);
    //Yoink ID and data size
    canID = rxMSG.id;
    dataLen = rxMSG.len;

    //Skip this frame if it isn't what we want
    if(canID != canRXID && dataLen != 8){continue;}

    //Print CAN Frame
    //Serial.println("Sending CAN Message");
    Serial.print("RX Data: [");
    for(char i = 0; i < 7; i++){
      Serial.print(rxMSG.data[i], BIN);
      Serial.print(", ");
    }
    Serial.print(rxMSG.data[7], BIN);
    Serial.println("]");

    //Search for free space in the buffer
    for(char i = 0; i < bufSize; i++){
      if(rxFlagBuf[i] == 0){
        rxFlagBuf[i] = 1;
        rxBuffer[i] = rxMSG;  
        break;
      }
    }
  }

  //Search for any CAN messages to send in buffer
  for(char i = 0; i < bufSize; i++){

    //Send any unsent messages
    if(txFlagBuf[i] == 1){
      txMSG = txBuffer[i];
      //Print CAN Frame
      //Serial.println("Sending CAN Message");
      Serial.print("Data: [");
      for(char i = 0; i < 7; i++){
        Serial.print(txMSG.data[i], BIN);
        Serial.print(", ");
      }
      Serial.print(txMSG.data[7], BIN);
      Serial.println("]");

      //Send message
      char ok = can.tryToSend(txMSG);

      //Keep trying if there was a failure
      while(!ok){
        ok = can.tryToSend(txMSG);
      }

      //Set flag to 0 to mark it as free space
      txFlagBuf[i] = 0;
    }
  }
}}

void loop1(){
  while(true){
  ESTOPCOUNT = digitalRead(ESTOP);
  if(ESTOPCOUNT > 0){
    Serial.println(millis());
    while(ESTOPCOUNT > 0){
      //Serial.print("Estop counter: "); Serial.println(ESTOPCOUNT);
      uint8_t stop = digitalRead(ESTOP);
      if(stop){
        ESTOPCOUNT = ESTOPCOUNT + 1;
      }else{
        ESTOPCOUNT = ESTOPCOUNT - 1;
      }
      if(ESTOPCOUNT > 10){
        STOPTHISMADNESS = 1;
        Serial.println(millis());
        break;
      }
    }
  }
  while(STOPTHISMADNESS){}

  for(char i = 0; i < bufSize; i++){

    //Check if the buffer entry is ready
    if(rxFlagBuf[i] == 1){

      //Decode buffer entry
      canDecode(rxBuffer[i].data);
      Serial.println(modeFlag);
      if(modeIO == 1){
        //Read stuff
        switch(modeFlag){
            //Analog Case
            case 0:
              writeAnalog(pinNum, dataSeg);
              Serial.print("Wrote "); Serial.print(dataSeg); Serial.print(" to pin "); Serial.println(pinNum);
            break;

            //Digital Case
            case 1:
              digitalWrite(digiPins[pinNum], dataSeg);
              Serial.print("Wrote "); Serial.print(dataSeg); Serial.print(" to pin "); Serial.println(pinNum);
            break;

            //Bulk Digital Case
            case 2:
              writeManyDigital(bulkDigi, dataSeg);
            break;

            //PWM Case
            case 3:
              setPWM(pinNum, dataSeg, (pwmDuty/255.0));
              if(pwmDuty == 0){
                pwmsEnabled[pinNum] = 0;
              }else{
                pwmsEnabled[pinNum] = 1;
              }
            break;
          }
        txBuffer[i] = canEncode(0, 0, 0);
        txFlagBuf[i] = 1;
        rxFlagBuf[i] = 0;
      }else{
        rxFlagBuf[i] = 0;
      }
    }
  }
  
}}