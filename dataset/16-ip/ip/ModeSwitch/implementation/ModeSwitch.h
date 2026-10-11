#if !defined(__MODESWITCH_H__)
#define __MODESWITCH_H__

#include "IP.h"

void ModeSwitchFun(void *p);

/* 模式切换 */
typedef struct __ModeSwitch {
    /* 接口函数 */
    Fun fun;

    /* 输入端口 */
    float32 *pGyroRate; /* 陀螺角速度数组指针 */
    unint32 flgSP;      /* 见太阳标志 */
    float32 royaw;      /* 太阳滚动 */
    float32 piyaw;      /* 太阳俯仰 */

    /* 输出端口 */
    unint32 m_workMode; /* 工作模式 */

    /* 输入输出端口 */
    /* 无 */

    /* 状态变量 */
    unint32 m_countMode;
    unint32 m_countPublic;

    /* 参数变量 */
    unint32 time_D2P; /* 速率阻尼连续稳定转俯仰搜索时间（控制周期） */
    unint32 time_D2P_overtime; /* 速率阻尼不能稳定转俯仰搜索时间（控制周期） */
} ModeSwitch;

#endif // __MODESWITCH_H__
