#if !defined(__POWER_ON_JUDGE_H__)
#define __POWER_ON_JUDGE_H__

#include "IP.h"

/* 设备状态 */
#define DEV_POWERON 0xFF /* 设备加电 */
#define DEV_INVALID 0x00 /* 设备不当班/不健康/断电状态 */

#define IPCALL(IP) (IP.fun(&IP))

/* IP句柄函数类型 */
typedef void (*Fun)(void *);

typedef struct __PowerOnJudge {
    /* 入口函数句柄 */
    Fun fun;

    /* 输入端口 */
    unint32 powerState; /* 加电状态 */

    /* 输出端口 */
    unint32 bPowerOnOk; /* 加电完成标志 */

    /* 输入输出端口 */
    /* 无 */

    /* 状态变量 */
    unint32 powerPr1;    /* 上周期的电源状态 */
    siint32 cntPowerOn;  /* 连续加电周期计数器 */
    siint32 cntPowerOff; /* 连续断电周期计数器 */

    /* 参数变量 */
    siint32 numOnPeriod;  /* 加电计数器阈值（配置参数） */
    siint32 numOffPeriod; /* 断电计数器阈值（配置参数） */
} PowerOnJudge;

extern void PowerOnJudgeFun(void *pIp);

#define IPCALL(IP) (IP.fun(&IP))

#endif // __POWER_ON_JUDGE_H__