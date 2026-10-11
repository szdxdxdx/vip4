#if !defined(__THREEAXISCONTROLLER_H__)
#define __THREEAXISCONTROLLER_H__

#include "IP.h"

void ThreeAxisControllerFun(void *p);

/* 控制器输入结构 */
typedef struct TAG_CONTROLLERIN {

    float32 Up; /* 输入参数 */
    float32 Ud; /* 输入参数 */
    float32 fy; /* 输出 */
} SController;

/* 控制器参数结构 */
typedef struct TAG_CONTROLLER_PARAM {
    float32 Kp; /* PD参数 */
    float32 Kd; /* PD参数 */
} SControllerParam;

/* 三轴控制器 */
typedef struct __ThreeAxisController {
    /* 接口函数 */
    Fun fun;

    /* 输入端口 */
    unint08 workMode;
    float32 *pAngle; /* 三轴姿态角数组指针 */
    float32 *pRate;  /* 三轴角速度数组指针 */

    /* 输出端口 */
    float32 u[3];

    /* 输入输出端口 */
    /* 无 */

    /* 状态变量 */
    float32 destRate[3]; /* 角速度偏置 */
    SController mController[3];

    /* 参数变量 */
    SControllerParam CTRL_PARAM_SAM[3]; /* 喷气参数 */

} ThreeAxisController;

#endif // __THREEAXISCONTROLLER_H__
