#include <Arduino.h>
#include <SPI.h>

// --- Pin definitions ---
#define PIN_DRDY 15
#define PIN_START 4
#define PIN_RESET 2

#define PIN_SCK 18
#define PIN_MISO 19
#define PIN_MOSI 23
#define PIN_CS 5

#define PIN_BUZZER 22   // Digital pin connected to the buzzer

// ADS1292R: 9 bytes per frame (3 status + 3 ch1 + 3 ch2)
#define FRAME_BYTES 9

// SPI: CPOL=0, CPHA=1 = SPI_MODE0
// Data reads can go faster but 100kHz is safe for all operations
SPISettings ADS_SPI_SETTINGS(100000, MSBFIRST, SPI_MODE0);

// Inter-byte delay required by datasheet (4 tCLK @ 512kHz = ~8us)
#define INTER_BYTE_DELAY_US 10

bool streaming = false;

// Low-level SPI transfer: CS held low for entire message
void ads_transfer(const uint8_t *tx, uint8_t *rx, size_t len) {
    SPI.beginTransaction(ADS_SPI_SETTINGS);
    digitalWrite(PIN_CS, LOW);
    delayMicroseconds(2);  // tCSSC: CS low to first SCLK setup

    for (size_t i = 0; i < len; i++) {
        uint8_t out = tx ? tx[i] : 0x00;
        uint8_t in  = SPI.transfer(out);
        if (rx) rx[i] = in;

        // Inter-byte gap required for multi-byte commands
        if (i < len - 1) {
            delayMicroseconds(INTER_BYTE_DELAY_US);
        }
    }

    // tSCCS: at least 3 tCLK before CS high (~6us @ 512kHz)
    delayMicroseconds(8);
    digitalWrite(PIN_CS, HIGH);
    SPI.endTransaction();
    delayMicroseconds(2);
}

void ads_send_opcode(uint8_t opcode) {
    ads_transfer(&opcode, nullptr, 1);
}

// WREG: write one register
void ads_wreg(uint8_t address, uint8_t value) {
    uint8_t cmd[3] = {
        (uint8_t)(0x40 | (address & 0x1F)),  // First opcode byte
        0x00,                                  // n-1 = 0 (write 1 register)
        value                                  // Register value
    };
    ads_transfer(cmd, nullptr, 3);
    delayMicroseconds(INTER_BYTE_DELAY_US);
}

// Read FRAME_BYTES while keeping CS low (used in RDATAC mode)
void ads_read_frame(uint8_t *out) {
    ads_transfer(nullptr, out, FRAME_BYTES);
}

// Returns expected total length of a command given its first byte
uint8_t command_length(uint8_t first_byte) {
    if ((first_byte & 0xE0) == 0x40) return 3;  // WREG
    if (first_byte == 0xF0)          return 2;  // buzzer command
    return 1;                                   // everything else: SDATAC(0x11), RDATAC(0x10), START(0x08), STOP(0x0A)
}

void ads_reset() {
    pinMode(PIN_RESET, OUTPUT);
    digitalWrite(PIN_RESET, LOW);
    delay(1);
    digitalWrite(PIN_RESET, HIGH);
    delay(1);  // 18 tCLK @ 512kHz ≈ 35us; 1ms is safe

    // Send RESET opcode as fallback
    delay(500);  // Wait for ADS power-on
    ads_send_opcode(0x06);  // RESET
    delay(1);
}

void activate_buzzer(uint8_t value) {
    if (value == 0x01) {
        tone(PIN_BUZZER, 1000);
    }
    else if (value == 0x00) {
        noTone(PIN_BUZZER);
    }
}

void handle_serial_commands() {
    static uint8_t cmd_buf[8];
    static uint8_t cmd_idx = 0;
    static uint8_t cmd_total = 0;

    while (Serial.available()) {
        uint8_t byte = Serial.read();

        if (cmd_idx == 0) {
            cmd_total = command_length(byte);
        }

        cmd_buf[cmd_idx++] = byte;

        if (cmd_idx >= cmd_total) {
            // Full command received — process it
            uint8_t opcode = cmd_buf[0];

            if (cmd_total == 1) {
                // Single-byte opcode
                if (opcode == 0x10) {         // RDATAC
                    streaming = true;
                } else if (opcode == 0x11) {  // SDATAC
                    streaming = false;
                }
                ads_send_opcode(opcode);
            }
            else if (cmd_total == 2 && opcode == 0xF0) {
                activate_buzzer(cmd_buf[1]);
            }
            else if (cmd_total == 3 && (opcode & 0xE0) == 0x40) {
                // WREG: forward address and value
                ads_wreg(opcode & 0x1F, cmd_buf[2]);
            }

            cmd_idx = 0;
            cmd_total = 0;
        }
    }
}

// Setup & Loop
void setup() {
    Serial.begin(115200);

    pinMode(PIN_CS, OUTPUT);
    pinMode(PIN_DRDY, INPUT);
    pinMode(PIN_START, OUTPUT);

    pinMode(PIN_BUZZER, OUTPUT);

    digitalWrite(PIN_CS, HIGH);
    digitalWrite(PIN_START, LOW);

    SPI.begin(PIN_SCK, PIN_MISO, PIN_MOSI, PIN_CS);

    ads_reset();
}

void loop() {
    handle_serial_commands();

    // Only read data when in streaming mode and data is ready
    if (streaming && digitalRead(PIN_DRDY) == LOW) {
        uint8_t frame[FRAME_BYTES];
        ads_read_frame(frame);

        // Send raw frame directly to Python
        // Python knows the format: 3 status + 3 ch1 + 3 ch2
        Serial.write(frame, FRAME_BYTES);
    }
}