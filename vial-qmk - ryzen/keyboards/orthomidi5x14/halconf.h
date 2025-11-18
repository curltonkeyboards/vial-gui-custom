#pragma once

#define HAL_USE_SPI TRUE
#define HAL_USE_I2C TRUE
#define SPI_USE_WAIT FALSE
#define SPI_USE_MUTUAL_EXCLUSION FALSE
#define HAL_USE_ADC TRUE

#include_next <halconf.h>