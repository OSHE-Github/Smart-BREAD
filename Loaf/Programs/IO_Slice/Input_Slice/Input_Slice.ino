#include <SPI.h>
#include <mcp2515.h>
#include "MCP3208.h"

//MCP2515 Setup
const char CANCS = A2; 
const char ADCCS = A3; 
const char CANINT = 2;
const uint16_t canTXID = 100;

//Runtime Flags
const char canDebug = 0;

//Can Frame Vars
char dataLen = 0;
int16_t canID = 0;

//Decoded value vars
char modeIO = 0;
char modeFlag = 0 ; 
char pinNum = 0;
char res1 = 0;
char res2 = 0;
int16_t bulkDigi = 0;
char pwmDuty = 0;
int16_t dataSeg = 0; 

//Runtime Vars
uint16_t analog = 0;

//Create known IC objects
MCP2515 canBus(CANCS);
MCP3208 externADC;


void canDecode(uint8_t canData[]){
  char byte = canData[0];
  modeIO = (byte & 0b10000000) >> 7;
  modeFlag =  (byte & 0b01110000) >> 4;
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
}

void loop() {
  struct can_frame canMsg;

  //Check if there is a message
  if (canBus.readMessage(&canMsg) == MCP2515::ERROR_OK) {
    Serial.println("Can message recieved!");

    //Yoink ID and data size
    canID = canMsg.can_id;
    dataLen = canMsg.can_dlc;

    //CAN frame debugging
    if(canDebug == 1){
      Serial.print("Data from ID: 0x"); Serial.print(canID, HEX);
      Serial.print(" [Size: "); Serial.print(int(dataLen)); Serial.print("] RAW Data: ");
      for (int i = 0; i < canMsg.can_dlc; i++)  {
        Serial.print(canMsg.data[i], HEX);
        Serial.print(" ");
      }
      Serial.println();
    }

    //Decode the frame if it is of the expected length and ID
    if(canID = 0x1A3 && dataLen == 8){
      canDecode(canMsg.data);
      //Serial.println(int(modeFlag), BIN);
      if(modeFlag == 1){
        Serial.print("Reading analog pin: ");
        Serial.println(int(pinNum));

        analog = externADC.analogRead(int(pinNum));
        float voltage = (analog * 5.0) / 4095.0;
        Serial.print(int(analog)); Serial.println(" Counts");
        Serial.print(voltage); Serial.println(" V");
      }
      








    }
  }
}
