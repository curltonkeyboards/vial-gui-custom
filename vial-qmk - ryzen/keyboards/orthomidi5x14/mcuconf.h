#pragma once

#include_next <mcuconf.h>

// I2C Configuration
#undef STM32_I2C_USE_I2C1
#define STM32_I2C_USE_I2C1 TRUE

// SPI Configuration - Enable SPI2 with DMA
#undef STM32_SPI_USE_SPI2
#define STM32_SPI_USE_SPI2 TRUE

#undef STM32_SPI_SPI2_DMA_PRIORITY
#define STM32_SPI_SPI2_DMA_PRIORITY 2

#undef STM32_SPI_SPI2_TX_DMA_STREAM
#define STM32_SPI_SPI2_TX_DMA_STREAM STM32_DMA_STREAM_ID(1, 4)  // DMA1 Stream 4

#undef STM32_SPI_SPI2_RX_DMA_STREAM
#define STM32_SPI_SPI2_RX_DMA_STREAM STM32_DMA_STREAM_ID(1, 3)  // DMA1 Stream 3

// Enable DMA
#undef STM32_SPI_DMA_ERROR_HOOK
#define STM32_SPI_DMA_ERROR_HOOK(spip) osalSysHalt("DMA error")

// PLL Configuration (your existing settings)
#undef STM32_PLLM_VALUE
#undef STM32_PLLN_VALUE
#undef STM32_PLLP_VALUE
#undef STM32_PLLQ_VALUE

#undef STM32_HSECLK
#define STM32_HSECLK 8000000

#define STM32_PLLM_VALUE    (STM32_HSECLK/1000000)
#define STM32_PLLN_VALUE    192
#define STM32_PLLP_VALUE    4
#define STM32_PLLQ_VALUE    4

#undef STM32_ADC_USE_ADC1
#define STM32_ADC_USE_ADC1 TRUE

// ADC clock configuration
#undef STM32_ADC_ADCPRE
#define STM32_ADC_ADCPRE ADC_CCR_ADCPRE_DIV4

// GPT (General Purpose Timer) Configuration - TIM5 for loop timer ISR
// TIM5 is a 32-bit timer on APB1 (48MHz with prescaler), used to drive
// macro/loop playback at 1kHz independent of the main scan loop.
#undef STM32_GPT_USE_TIM5
#define STM32_GPT_USE_TIM5 TRUE

// USART Configuration for MIDI Serial
// Using USART1 on PA15 (TX) and PB3 (RX) - these are JTAG pins remapped to USART1
#undef STM32_SERIAL_USE_USART1
#define STM32_SERIAL_USE_USART1 TRUE
#undef STM32_SERIAL_USE_USART3
#define STM32_SERIAL_USE_USART3 FALSE