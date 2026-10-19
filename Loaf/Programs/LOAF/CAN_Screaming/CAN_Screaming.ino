#include "driver/twai.h"

// Hardware pins
#define CAN_TX_PIN GPIO_NUM_19
#define CAN_RX_PIN GPIO_NUM_18
uint32_t counter = 0;
uint32_t counter2 = 0;

void setup() {
  Serial.begin(115200);
  while (!Serial);
  Serial.println("ESP32 + MCP2561 Continuous Transmit (1Mbps)");

  // Initialize in Normal Mode to broadcast outward onto the bus
  twai_general_config_t g_config = TWAI_GENERAL_CONFIG_DEFAULT(CAN_TX_PIN, CAN_RX_PIN, TWAI_MODE_NORMAL); 
  twai_timing_config_t t_config = TWAI_TIMING_CONFIG_1MBITS();
  twai_filter_config_t f_config = TWAI_FILTER_CONFIG_ACCEPT_ALL();

  // Install the TWAI driver
  if (twai_driver_install(&g_config, &t_config, &f_config) != ESP_OK) {
    Serial.println("Failed to install TWAI driver.");
    return;
  }

  // Start the TWAI driver
  if (twai_start() != ESP_OK) {
    Serial.println("Failed to start TWAI driver.");
    return;
  }
  
  Serial.println("TWAI Driver active. Beginning broadcast.");
}

static void printFrame(const twai_message_t &msg) {
  Serial.printf("[rx] id=0x%03lX%s%s dlc=%u data=",
                (unsigned long)msg.identifier,
                msg.extd ? " ext" : "",
                msg.rtr ? " RTR" : "",
                msg.data_length_code);
  if (msg.rtr) {
    Serial.println("(remote frame, no payload)");
    return;
  }
  for (int i = 0; i < msg.data_length_code; i++) {
    Serial.printf("%02X ", msg.data[i]);
  }
  Serial.println();
}

void loop() {
  // Construct the CAN message frame
  twai_message_t tx_msg;
  twai_message_t rx_msg;
  //Basic Setup
  tx_msg.identifier = 0x1A3;
  tx_msg.extd = 0;
  tx_msg.data_length_code = 8;

  //Formatted CAN Message
  tx_msg.data[0] = 0b00010000;
  tx_msg.data[1] = 0b00000000;
  tx_msg.data[2] = 0b00000000;
  tx_msg.data[3] = 0b00000000;
  tx_msg.data[4] = 0b00000000;
  tx_msg.data[5] = 0b00000000;
  tx_msg.data[6] = 0b00000000;
  tx_msg.data[7] = 0b00000000;

  // Transmit immediately without blocking or waiting for bus clearance
  if (twai_transmit(&tx_msg, 0) == ESP_OK) {
    Serial.println("Transmitted A0 Request ");
  } else {
    Serial.println("Failed to transmit message. Check bus connection/termination.");
  }

  if (twai_receive(&rx_msg, pdMS_TO_TICKS(10)) == ESP_OK) {
      Serial.print("Received Message | ID: 0x");
      Serial.print(rx_msg.identifier, HEX);
      Serial.print(" | Format: ");
      Serial.print(rx_msg.extd ? "Extended (29-bit)" : "Standard (11-bit)");
      Serial.print(" | DLC: ");
      Serial.print(rx_msg.data_length_code);
      Serial.print(" | Data: ");

      if (!(rx_msg.rtr)) {
        for (int i = 0; i < rx_msg.data_length_code; i++) {
          Serial.print("0x");
          if (rx_msg.data[i] < 0x10) Serial.print("0");
          Serial.print(rx_msg.data[i], HEX);
          Serial.print(" ");
        }
      } else {
        Serial.print("[RTR Frame]");
      }
      Serial.println();
    }
  // Delay for exactly 1 second (1000 milliseconds)
  delay(1000); 
}
