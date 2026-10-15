#include <SPI.h>
#include <mcp2515.h>
#include "MCP3208.h"

//MCP2515 Setup
#define CANCS 16
#define CANINT 2
#define canTXID 100

//Digital pin setup
#define numDigital 8
const uint8_t digiPins[numDigital] {3, 4, 5, 6, 7, 8, 9, 10}; //DIO0, DIO1, DIO2, DIO3, DIO4, DIO5, DIO6, DIO7

//Analog pin Setup
#define ADCCS 17
#define numAnalog 8


//Runtime Flags
#define canDebug false

//Can Frame Vars
uint8_t dataLen = 0;
int16_t canID = 0;

//Decoded value vars
uint8_t modeIO = 0;
uint8_t modeFlag = 0 ; 
uint8_t pinNum = 0;
uint8_t res1 = 0;
uint8_t res2 = 0;
int16_t bulkDigi = 0;
uint8_t pwmDuty = 0;
int16_t dataSeg = 0; 

//Runtime Vars
uint16_t analog = 0;
char digital = 0;
uint16_t digitalBulk = 0;

//Create known IC objects
MCP2515 canBus(CANCS);
MCP3208 externADC;

struct can_frame canRX;
struct can_frame canTX;

//Decode the CAN message recieved into the required fields. Refer to I/O Slice CAN message spec for details.
void canDecode(uint8_t canData[]){
  char byte = canData[0];
  modeIO = (byte & 0b11000000) >> 6;
  modeFlag =  (byte & 0b00110000) >> 4;
  pinNum =  byte & 0b00001111;

  //Reserved data reading
  //res1 = canMsg.data[1];
  //res2 = canMsg.data[4];

  //PWM Duty cycle reading
  if(modeFlag == 2){pwmDuty = canData[5];}

  //Bulk Digital pin decoding
  if(modeFlag == 3){
    bulkDigi = canData[2];
    bulkDigi = (bulkDigi << 8) + canData[3];
  }
  
  //Data Segment Decoding
  dataSeg = canData[6];
  dataSeg = (dataSeg << 8) + canData[7];
}

//Encode a new message and return the encoded message
void canEncode(uint16_t bulkDigi, uint16_t dataSeg){

  //Info Byte encoding
  canTX.data[0] = 0b10000000;
  canTX.data[0] = canTX.data[0] + pinNum + (modeFlag << 4);

  //Reserved bits encoding
  canTX.data[1] = 0; canTX.data[4] = 0;

  //Bulk digital data encoding
  canTX.data[2] = char(bulkDigi >> 8);
  canTX.data[3] = char(bulkDigi & 0b0000000011111111);

  //Data segment encoding
  canTX.data[6] = char(dataSeg >> 8);
  canTX.data[7] = char(dataSeg & 0b0000000011111111);
  
  //We don't care about PWM Duty cycle on input slice
  canTX.data[5] = 0;
}


void setup() {
  //Serial Setup
  Serial.begin(115200);
  while (!Serial) {}

  //Reset the MCP2515 chip before we configure it
  canBus.reset();

  //Configure MCP3208 ADC and start it up at 12 bit resolution
  externADC.begin(ADCCS);
  externADC.analogReadResolution(12); 

  
  //Set up device for highest speed we can permit
  if (canBus.setBitrate(CAN_1000KBPS, MCP_16MHZ) == MCP2515::ERROR_OK) {}
  else {
    Serial.println("Error: Failed to set Bitrate/Clock configuration.");
    while(true){}
  }

  //SAet to normal mode and hang if it can't
  if (canBus.setNormalMode() == MCP2515::ERROR_OK) {}
  else {
    Serial.println("Error: Failed to set Normal Mode.");
    while(true){}
  }

  //Format outgoing CAN message
  canTX.can_id = canTXID;
  canTX.can_dlc = 8; 


  //Set up all digital pins to be inputs
  for(char i = 0; i < numDigital; i++){
    pinMode(i, INPUT);
  }
}

void loop() {
while(true){
  //Check if there is a message
  if (canBus.readMessage(&canRX) == MCP2515::ERROR_OK) {
    Serial.println("Can message recieved!");

    //Yoink ID and data size
    canID = canRX.can_id;
    dataLen = canRX.can_dlc;

    //CAN frame debugging
    if(canDebug){
      Serial.print("Data from ID: 0x"); Serial.print(canID, HEX);
      Serial.print(" [Size: "); Serial.print(dataLen); Serial.print("] RAW Data: ");
      for (int i = 0; i < canRX.can_dlc; i++)  {
        Serial.print(canRX.data[i], HEX);
        Serial.print(" ");
      }
      Serial.println();
    }

    //Skip this frame if it isn't what we want
    if(canID != 0x1A3 && dataLen != 8){continue;}

    //Decode the frame if it is of the expected length and ID
    canDecode(canRX.data);      
    //Mode 0 = Analog
    if(modeFlag == 0){
      Serial.print("Reading analog pin: "); Serial.println(int(pinNum));

      analog = externADC.analogRead(pinNum);
      float voltage = (analog * 5.0) / 4095.0;
      Serial.print(analog); Serial.println(" Counts");
      Serial.print(voltage); Serial.println(" V");

      canEncode(bulkDigi, analog);
      if(canBus.sendMessage(&canTX) == MCP2515::ERROR_OK){
        Serial.print("Message Sent! ID: 0x");
        Serial.println(canTX.can_id, HEX);
      }else{
        Serial.println("Error sending message! Check bus wiring, power, and termination.");
      }
    }

    if(modeFlag == 1){
      Serial.print("Reading digital pin: "); Serial.println(int(pinNum));
      digital = digitalRead(digiPins[pinNum]);
      canEncode(bulkDigi, digital);
      if(canBus.sendMessage(&canTX) == MCP2515::ERROR_OK){
        Serial.print("Message Sent! ID: 0x");
        Serial.println(canTX.can_id, HEX);
      }else{
        Serial.println("Error sending message! Check bus wiring, power, and termination.");
      }






    }
  }
}}
