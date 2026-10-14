#if !defined(__CS_ORBITCOMPUTATION_H__)
#define __CS_ORBITCOMPUTATION_H__

#include "../../IP.h"

// 函数声明
void CS_OrbitComputationFun(void *p);

typedef struct TAG_ORBIT_PARAMETERX
{
    /* 轨道19根数 */
    /* start of Param19 固定结构勿改 */
    float64 t0;                        /* 使用的轨道参数的参考时刻 */
    float64 deltaa0;                   /* t0时刻轨道拟平半长轴减去地球半径之后的值 */
    float64 adelta;                    /* 拟平半长轴的一阶长期系数 */
    float64 i0;                        /* t0时刻拟平轨道倾角 */
    float64 omg0;                      /* t0时刻拟平升交点赤经 */
    float64 omg1;                      /* 拟平升交点赤经的一阶长期项系数 */
    float64 kesid;                     /* ξ_mean的一阶长期项系数 */
    float64 etad;                      /* η_mean的一阶长期项系数 */
    float64 w1;                        /* 拟拟平近地点幅角的一阶长期项系数 */
    float64 etam;                      /* ηm=-kesi2/w1, kesi2为kesi的二阶摄动系数 */
    float64 a;                         /* Xi和Eta的长周期变化幅度 */
    float64 beta;                      /* Xi和Eta的长周期变化相位 */
    float64 lmd0;                      /* t0时刻λ的初值 */
    float64 lmd1;                      /* λ的长期项系数 */
    float64 lmd2;                      /* λ的二阶长期系数 */
    float64 lmdg;                      /* 格林尼治恒星时角 */
    float64 msun0;                     /* t0时刻太阳平近点角 */
    float64 wsun;                      /* t0时刻太阳的近地点角 */
    float64 omgsun;                    /* t0时刻太阳的升交点赤经 */
    /* end of Param19 固定结构勿改 */
    float64 UTC0;                      /* 星时计时零点相对 GPS 计时零点的时间间隔 */
    float64 qd[4];                     /* 岁差章动四元数，qJD[0]～qJD[2]为矢量部分，qJD[3]为标量部分 */
    /* end of Param23 固定结构勿改 */
} SOrbitParameterX;


/* 轨道输出参数 */
typedef struct TAG_ORBIT_DATAX
{
    float64  a;                         /* 外推轨道六根数参数a，轨道半长轴 */
    float64  i;                         /* 外推轨道六根数参数i，轨道倾角 */
    float64  e;                         /* 外推轨道六根数参数e，轨道偏心率 */
    float64  f;                         /* 外推轨道六根数参数f，u-w */
    float64  u;                         /* 外推轨道六根数参数u，轨道幅角 */
    float64  w;                         /* 外推轨道六根数参数ω，近地点幅角 */
    float64  omg;                       /* 外推轨道六根数参数Ω，升交点赤经 */
    float64  M;                         /* 外推轨道六根数参数M */
    float64  pos[3];                    /* 惯性坐标系位置x/y/z */
    float64  rate[3];                   /* 惯性坐标系速度x/y/z */
    float64  w0;                        /* 计算的轨道角速度 */
    float64  r;                         /* 计算的地心距离 单位km */
    float64  cosrou;                    /* 地球半张角余弦 */
    float64  us;                        /* 太阳星历计算的太阳轨道的幅角u */
    float64  l1;                        /* 计算的经度及地心经度 */
    float64  l;                         /* 计算的经度及地理经度 */
    float64  delta;                     /* 计算的经度及地心纬度 */

    /* 平根数输出 */
    float64  ap;
    float64  omgp;
    float64  kesip;
    float64  etap;
    float64  lmdp;
    float64  ip;

    float64  kesi;                      /* ξ */
    float64  eta;                       /* η */
    float64  lmd;                       /* lmd */

    float64  sb[3];                     /* 本体太阳矢量 */
    float64  si[3];                     /* 太阳矢量在惯性系表示 */
    float64  so[3];                     /* 太阳矢量在轨道系表示 */
    float64  usun;                      /* 太阳轨道的幅角u */
    float64  coi[3][3];                 /* 从惯性系到轨道系的姿态转移矩阵 */
    float64  VRe[3];                    /* 地心矢量在惯性系的表示 */

    float64  qoi[4];                    /* 惯性至轨道坐标系四元素 */
    float64  w0i[3];                    /* 考虑轨道进动的轨道系相对于惯性系J2000.0的角速度 */

    float64  lmdG;                      /* λG */
    float64  Cz_lmdG[3][3];             /* Cz_λG */

    unint32  F_OrbAbnorm;               /* w0校验通过标志 */

} SOrbitDataX;

// IP 结构体定义
typedef struct __CS_OrbitComputation
{
    /* 函数接口 */
    // Fun fun;

    /* 输入变量 */
//    unint32 m_WorkMode;                                 /* 当前模式 */
//    float64 m_starTime_Next;                            /* 下周期星时 t_next */
//    unint32 csOrbOtherPara_FP_OrbUpdate[14];            /* 轨道根数更新允许标志 (1: 允许, 0: 禁止 ) */
//    unint32 csOrbOtherPara_FP_UseOtherOrb;              /* 允许使用其他轨道参数标志 (0: 不允许，1: 允许) */
//    unint32 csOrbOtherPara_FP_WoPrecession;             /* ωoi计算是否考虑轨道进动 (0: 不考虑，1: 考虑) */
//    unint32 csOrbDataOther_F_DTOrbitEUpdate;            /* */
    SOrbitParameterX pOrbI;                             /* 注入轨道 */
    SOrbitParameterX pOrbG;                             /* GPS轨道 */
//    unint32 pGpsPara_FS_UseType;                        /* 引入GPS轨道计算      =0,轨道计算不引入GPS;=1,引入GPS通道板;=2,引入GPS轨道板 */

    /* 输出变量 */
//    unint32 csOrbitErrJData_F_TurnAAM;
//    unint32 pObtOut_FV;                                 /* 轨道数据有效标志(0:无效，1:有效) */
//    unint32 pObtOut_F_SunlightZone[3];                  /* 阳照区标志 */
//    unint32 pObtOut_FV_NoInsert;
//    SOrbitDataX pOrbData;
//
//    /* 输入输出变量 */

    /* 状态变量*/
    SOrbitParameterX pOrbPara;
    unint32 csOrbitErrJData_Cnt_NoOrb;

    /* 参数变量 */
//    float64 csOrbInjChkPara_calc_r_norm;                /* 地心距离的正常值       r_norm */
//    float64 csOrbInjChkPara_calc_w0_norm;               /* 轨道角速度ω0的正常值   ω0_norm */
//    float64 csOrbInjChkPara_calc_cosp_norm;             /* cosρ的正常值           cosρ_norm */
//    float64 csOrbInjChkPara_calc_Lmt_dw0;               /* 轨道角速度ω0的误差阈值 Lmt_Δω0 */
//    float64 csOrbInjChkPara_Lmt_dT;                     /* 轨道时间与当前星时误差阈值 Lmt_Δt */

//    float64 pOCP_Mu;                                    /* 引力常数 */
//    float64 pOCP_Re;                                    /* 地球赤道半径 */
//    float64 pOCP_We;                                    /* 地球自转角速度 */
//    float64 pOCP_A2;                                    /* 地球带谐项系数 */
//    float64 pOCP_Hco2;                                  /* 二氧化碳层距地面高度 */
//    float64 pOCP_dMSun;                                 /* 太阳轨道平近点角的变化率 */
//    float64 pOCP_eSun;                                  /* 太阳轨道的偏心率 */
//    float64 pOCP_iSun;                                  /* 太阳轨道的倾角 */

//    unint32 csOrbitErrJPara_Num_NoOrb;
//    unint32 csOrbitErrJPara_FS_NoOrbPro;

} CS_OrbitComputation;

#endif // __CS_ORBITCOMPUTATION_H__