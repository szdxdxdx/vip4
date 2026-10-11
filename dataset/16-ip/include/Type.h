#if !defined(__TYPE_H__)
#define __TYPE_H__

#include "std_utils.h"

#define TRUE  0xEB90146Fu
#define FALSE 0u
#define ABS(a)        (((a) > 0) ? (a) : -(a))
#define MIN(a, b)     (((a) > (b)) ? (b) : (a))

#define SAM_DAMP      0x00    /* SAM速率阻尼方式 */
#define SAM_PITCH     0x11    /* SAM俯仰搜索方式 */
#define SAM_ROLL      0x22    /* SAM滚动搜索方式 */
#define SAM_CRUISE    0x33    /* SAM巡航方式 */
#define NOCTRL        0x44    /* 不控 */


/* 陀螺数据 */
typedef struct TAG_DIGITAL_GYRO_DATA
{
    unint32     powerstate;      /* 陀螺加电状态 */
    float32     wa[9];       /* 陀螺角速度模拟 */

} SGyroRawData;

/* 陀螺数据 */
typedef struct TAG_GYRO_STATE
{

    unint08 countPick[9];  /* 陀螺原始数据处理时,剔野计数器 */
    float32 wal[9];        /* 上周期陀螺角速度模拟量 */
    unint08 JoinTotal;     /* 参加定姿的陀螺个数 */
    unint16 gyroStatus0;   /* 陀螺状态旧 */
    unint16 gyroStatus1;   /* 陀螺状态新 */
    unint32 SignFlag[9];   /* 参加定姿的陀螺序号 */
    unint32 StateFlag[9];  /* 陀螺状态标志 */
    float32 Rtemp[3][5];   /* 矩阵计算结果 */

} SGyroState;

/* 姿态结构 */
typedef struct TAG_ATTITUDE_PARA
{
    float32     angle[3];    /* 三轴姿态角 */
    float32     rate[3];    /* 三轴角速度 */
}SAttitude;

/* 敏感器输入结构 */
typedef struct TAG_DSS_DATA
{
    unint32     SP;
    float32     royaw;
    float32     piyaw;

}SDSSData;


/* 敏感器输入结构 */
typedef struct TAG_DSS_RAW_DATA
{
    unint32     SP;
    float32     ang1;
    float32     ang2;
}SDSSRawData;

/* 控制器输入结构 */
typedef struct TAG_CONTROLLERIN
{

    float32     Up;    /* 输入参数 */
    float32     Ud;    /* 输入参数 */
    float32     fy;    /* 输出 */

}SController;

/* 控制器参数结构 */
typedef struct TAG_CONTROLLER_PARAM
{
    float32     Kp;       /* PD参数 */
    float32     Kd;       /* PD参数 */
} SControllerParam;


/* 陀螺三轴角速度 */
typedef struct TAG_GYRO_RATE
{
    float32     rate[3];
}AGyroRate;

/* 伪速率调制器结构 */
typedef struct TAG_MODULATOR
{
    // unint16        wPulse;
    unint08     Yp[3];    /* 脉冲方向输出 */
    unint08     Yn[3];    /* 脉冲方向输出 */
}PModulator;

#endif // __TYPE_H__
