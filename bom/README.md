# Bill of Materials (V1 Prototype)

This folder contains the minimum required materials to reproduce the project, along with example supplier links, estimated pricing, cheaper alternatives, and practical purchasing tips.

## Notes

- Prices are estimates based on listings available at the time of writing and may change over time.
- Shipping/import costs can vary by country and region.

## Price Table (same as in .csv file)

| Vendor | Item | Quantity | Price (USD) | Shipping |
| :----------- | :--- | :------- | ----------: | -------: |
| [AliExpress](https://www.aliexpress.com/item/3256806677478076.html) | ESP32 | 1x (Type C 30Pin) | $ 9.39 | Usually Free |
| [AliExpress](https://www.aliexpress.com/item/3256805267039105.html) | ADS1292R Module | 1x | $ 35.66 | $ 5.87 |
| [OpenBCI Shop](https://shop.openbci.com/products/ten20-conductive-paste-8oz-jar) | Conductive Paste Ten20 | 1x | $24.99 | Vary |
| [AliExpress](https://pt.aliexpress.com/item/1005005209000522.html) | Gold Cup Electrodes | 3x | $ 10.00 | $ 5.43 |
| [AliExpress](https://www.aliexpress.com/item/1005007046465880.html) | Jumper Cables | 3Pcs-1Set | $ 2.59 | Usually Free |
| [AliExpress](https://www.aliexpress.us/item/3256807269711005.html) | 3.5mm Jack to Wire | 1x (Male 3 Pole) | $ 2.00 | Usually Free |
| [AliExpress](https://www.aliexpress.com/item/3256810240512195.html) | Protoboard | 1x | $ 1.94 | Usually Free |
| [AliExpress](https://www.aliexpress.us/item/3256806910268724.html) | Buzzer Module | 1x (passive buzzer) | $ 2.41 | Usually Free |
| [AliExpress](https://www.aliexpress.com/item/3256806674760478.html) | Capacitors | 1x 47pF, 1x 100 nF | $ 6.81 | Usually Free |

- Approximate Total (USD): **$ 107.09**
- Approximate Total (BRL): **R\$ 535,45**

## Required Tools

- Soldering iron
- USB-C cable for ESP32
- Computer with Python 3.8+
- Tape for attaching the electrodes

## Essential Materials

The absolute necessary materials are:

- ESP32
- ADS1292R module
- Connectors/Jumpers (you probably already have)
- Gold cup EEG electrodes (3 electrodes required: signal, reference, and bias)
- 3.5 mm Jack (Male TRS - used as a detachable connector for electrodes to ADS module)
- Conductive paste for EEG

## Good to have

The following materials are optional but were used in the original prototype and may help reproduce similar results:

- Protoboard (you probably already have)
- Buzzer Module
- Capacitors

The **buzzer module** is optional: since the person performing the experiment may not be looking at the screen during acquisition, the buzzer provides real-time auditory neurofeedback when alpha activity surpasses a defined threshold. It can easily be replaced by another feedback method, such as an LED indicator or software notification.

The **capacitors** were added to improve SPI signal stability and power supply decoupling between the ESP32 and the ADS1292R module.

## Cheaper Alternatives

Unfortunately, the most expensive component is also the most important: the ADS1292R module. A cheaper alternative is to purchase the ADS1292R chip directly (ADS1292RIPBSR) together with a prototype PCB, which can reduce the total cost of the module to roughly one third. However, this approach requires precise soldering of fine-pitch pins, additional circuit assembly, and slightly different wiring, which are not covered in this project. Most cost reductions can therefore only be made on other components without significantly affecting the prototype:

- **ESP32, jumpers, protoboard and buzzer/LED** can be bought togheter as a kit. There are several options which also includes resistors, buttons and other modules up to $ 15.00 that can be useful for other projects as well.
- For the **EEG conductive paste**, there are less expensive alternatives (and brands). Although ECG gels can work, it is much more difficult to keep the electrodes adhered to the skin, so I would advise sticking with EEG-specific ones.
- Cheaper copper electrode alternatives also exist, and **Gold Cup Electrodes** are often less expensive when purchased in larger quantities.
- The **3.5 mm Jack** can be taken from any old disposable earphones or audio device (as long as they are TRS - Tip, Ring, Sleeve) to be connected to the 3 electrodes.
