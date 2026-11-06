#include "driver/twai.h"

// --- Define your ESP32 Pins ---
#define CAN_TX_PIN GPIO_NUM_19
#define CAN_RX_PIN GPIO_NUM_18

void setup() {
  Serial.begin(115200);
  while(!Serial) { delay(10); }
  
  Serial.println("\n--- ESP32 TWAI/CAN Listener Active ---");

  // Initialize configuration structures at a strict 500kbps clock rate
  twai_general_config_t g_config = TWAI_GENERAL_CONFIG_DEFAULT(CAN_TX_PIN, CAN_RX_PIN, TWAI_MODE_NORMAL);
  twai_timing_config_t t_config  = TWAI_TIMING_CONFIG_500KBITS();
  twai_filter_config_t f_config  = TWAI_FILTER_CONFIG_ACCEPT_ALL();

  // Install the TWAI driver
  if (twai_driver_install(&g_config, &t_config, &f_config) == ESP_OK) {
    Serial.println("Driver installed successfully.");
  } else {
    Serial.println("Failed to install driver.");
    while (1);
  }

  // Start the TWAI driver module
  if (twai_start() == ESP_OK) {
    Serial.println("TWAI Driver Started. Waiting for Pico 2 frames...");
  } else {
    Serial.println("Failed to start driver.");
    while (1);
  }
}

void loop() {
  twai_message_t message;
  
  // Wait indefinitely or handle arriving packets as they hit the RX buffers
  if (twai_receive(&message, pdMS_TO_TICKS(1000)) == ESP_OK) {
    Serial.print(">>> ACKed Packet from Pico 2! ID: 0x");
    Serial.print(message.identifier, HEX);
    Serial.print(" | DLC: ");
    Serial.print(message.data_length_code);
    Serial.print(" | Data: ");
    
    for (int i = 0; i < message.data_length_code; i++) {
      Serial.print(message.data[i], HEX);
      Serial.print(" ");
    }
    Serial.println();
  } else {
    // Keeps you updated if the bus is staying quiet
    Serial.println("Bus Idle... Waiting for hardware edge triggers.");
  }
}
