/* std_addr.h - 规范化地址操作定义头文件 */
/* 2013.12.31, created */

#ifndef STD_ADDR_H
#define STD_ADDR_H

#include "std_basal.h"

/* PROM地址有效性判断 */
#define PROM_VALIDATE(addr)         ((PROM_STARTADDR <= (addr)) && ((addr) <= PROM_ENDADDR))

/* RAM地址有效性判断 */
#define RAM_VALIDATE(addr)          ((RAM_STARTADDR  <= (addr)) && ((addr) <= RAM_ENDADDR))

/* 地址是否对齐判断;使用原则,写入时严格判断是否4字节对齐,读出时自动对齐 */
#define IS_ADDR_ALIGN(addr)         (((addr) & 0x3) == 0)


/* 往硬件地址写数据宏函数 */
#define ADDR_WRITE(addr, value)     ((*((volatile unint32 *)(addr))) = (value))

/* 从硬件地址读32位数据宏函数 */
#define ADDR_READ(addr)             ((*((volatile unint32 *)(addr))))

/* 从硬件地址读32位数据宏函数 */
#define ADDR_READ32(addr)           ADDR_READ(addr)

/* 从硬件地址读8位数据宏函数 */
#define ADDR_READ8(addr)            (ADDR_READ(addr) & 0xFF)

/* 从硬件地址读16位数据宏函数 */
#define ADDR_READ16(addr)           (ADDR_READ(addr) & 0xFFFF)


/* 将地址值转换为32位无符号整型数 */
#define ADDR_TO_ABSUI(ptr)          ((unint32)(ptr))


#endif