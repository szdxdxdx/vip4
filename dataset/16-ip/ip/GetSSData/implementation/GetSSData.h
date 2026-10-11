#if !defined(__GETSSDATA_H__)
#define __GETSSDATA_H__

#include "IP.h"

void GetSSDataFun(void *p);

/* 太敏数据采集 */
typedef struct __GetSSData {
    /* 接口函数 */
    Fun fun;

    /* 输入端口 */
    /* 无 */

    /* 输出端口 */
    float32 royaw; /* 太敏滚动角 */
    float32 piyaw; /* 太敏俯仰角 */
    unint08 flgSp; /* 见太阳标志 */

    /* 输入输出端口 */
    /* 无 */

    /* 状态变量 */
    /* 无 */

    /* 参数变量 */
    unint16 ADDR_AD_START; /* AD采集启动地址 0xA000 */
    unint16 AD_SS_LO4;     /* AD采集数据低4位地址 0xA003 */
    unint16 AD_SS_HI8;     /* AD采集数据高8位地址 0xA001 */
    unint16 SP_ADDR;       /* 见太阳标志地址 0xE000 */
    unint08 SP_BIT;        /* 见太阳标志位 5 */
    unint08 chnl[2];       /* AD采集通道号 */
} GetSSData;

#endif // __GETSSDATA_H__
