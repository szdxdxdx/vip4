#if !defined(__CS_ATTCTRL_PROPEL__)
#define __CS_ATTCTRL_PROPEL__

#include "../IP.h"

void CS_AttCtrl_PropelFun(void *p);

typedef struct TAG_PHASE_PARAMETERX
{
    float64 ThetaD;         /* 死区阀值,deg                   θD */
    float64 ThetaB;         /* 大推力区阀值,deg               θB */
    float64 Dtheta;         /* 参数,deg                       dθ */
    float64 ThetaV;         /* 步进区阀值,deg                 θV */
    float64 dThetaS;        /* 小推力区角速度最大值,deg/s    dθS */
    float64 dThetaV;        /* 步进区角速度最大值,deg/s      dθV */
    float64 dThetaL;        /* 限速值,deg/s                  dθL */
    float64 dThetaLL;       /* 限速值,deg/s                 dθLL */
    float64 Kj1;            /* 开关线斜率,s                   s1 */
    float64 Kj2;            /* 开关线斜率,s                   s2 */
    float64 KJ;             /* 步进区参数,1/s                 Kj */
    float64 Tmax;           /* 最大喷气脉宽,s               tmax */
    float64 Tmin;           /* 最小喷气脉宽,s               tmin */

} SPhaseParamX;


/* 模式切换指令处理 */
typedef struct __CS_AttCtrl_Propel
{
    /* 接口函数 */
    Fun     fun;

    /* 输入端口 */
    unint32 csModeData_F_StopCtrl;                      /* 星上停控标志 */
    unint32 m_WorkMode;                                 /* 当前模式 */
    float64 ModeObjectTimer_Mode[14];                   /* 模式执行时间 */
    unint32 csWacqData_m_SubMode;                       /* 全捕子模式字 */
    float64 csAttCoreData_A_c[3];                       /* 滚动/俯仰/偏航姿态角控制误差 */
    float64 csAttCoreData_Rate_c[3];                    /* 滚动/俯仰/偏航姿态角速度控制误差 */
    unint32 csModeData_F_PanelUnfold;                   /* 帆板展开标志，0：未展开，1：展开 */
    unint32 csJPCPara_FU;                               /* 姿控发动机状态标志 (0:主、备分支均不工作;1:姿控用主份推力器;2:姿控用备份推力器;3:姿控用主、备双份推力器) */
    unint32 csJPCData_FJ[3];                            /* FJXY,XZ,YZ */
    unint32 csCtrlerOtherPara_FP_RWorCMGC[14];          /* RWorCMG控制标志(1:允许;0: 禁止) */
    unint32 csJPCData_F_UldT;                           /* 喷气卸载标志(1: 喷气卸载,0: 不卸载) */
    unint32 csSGAttAcqData_F_EarthAcq;                  /* 全捕模式进行地地或太地捕获标志标志,0太地捕获方式，1地地捕获方式 */
    unint32 csSGAttAcqData_F_YawCapt;                   /* 太地捕获时允许转地球捕获标志 */
    unint32 csIomScanPara_FP_GK_JetBack;                /* 惯性定向/扫描结束后回正常模式的控制方式
                                                            0：动量轮或者CMG控制；1：喷气控制 */
    unint32 csIomScanData_SMODE;                        /* 惯性定向阶段标志字
                                                            0：将星体惯性角速度ωri从轨道角速度ωoi减为零
                                                            1：从阻尼后初始姿态q机动至凝视标定姿态或扫描起速前姿态并保持定向
                                                            2：由惯性定向起速ωCam_Slew机动q_SlewStop并停止运动
                                                            10：返回对地零姿态
                                                            11：建立轨道角速度 */
    float64 csCtrlerDataJs_Use[3][3];                   /* 当前选用的星体惯量矩阵 */

    /* 输出端口 */
    float64 csJPCData_t[12];                            /* Thr[i].t 各姿控喷管本拍输出喷气脉宽 */
    float64 csJPCData_a[3];                             /* 喷气三轴角加速度 */
    float64 csJPCData_a2[3];                            /* 喷气三轴角加速度,仅用于推力器故障诊断 */
    float64 csJPCData_SumTp2[3];                        /* 正XYZ轴喷气总计脉宽,仅用于推力器故障诊断 */
    float64 csJPCData_SumTn2[3];                        /* 负XYZ轴喷气总计脉宽,仅用于推力器故障诊断 */
    float64 csJPCData_t_AC[12];                         /* Thr[i].t_AC 各轨控喷管输出喷气脉宽 */
    unint32 csJPCData_F_st[3];                          /* 三轴喷气状态 */
    float64 csJPCData_apn[3][2];                        /* 三正一斜,ThrGr.a_px,ThrGr.a_nx,ThrGr.a_py,ThrGr.a_ny,ThrGr.a_pz,ThrGr.a_nz */

    /* 输入输出端口 */
    float64 csJPCData_mPhase_T[3];                      /* 喷气脉宽,s       t_axis */
    float64 csJPCData_mPhase_ThetaC_pst[3];             /* 姿态角阀值,deg          */
    float64 csJPCData_mPhase_Region[3];                 /* 相区             Zones  */
    unint32 csJPCData_F_Jet[3];                         /* F_Jetx,y,z */
    float64 csJPCData_mPhase_FJB[3];                    /* 喷气状态         F_Jet  */

    unint32 csJPCData_F_AssignUse[12];                  /* 推力器i本周期产生某轴的力矩标志 */
    float64 csJPCData_SumTn[3];                         /* 负XYZ轴喷气总计脉宽 */
    float64 csJPCData_SumTp[3];                         /* 正XYZ轴喷气总计脉宽 */

    /* 状态变量 */

    /* 参数变量 */
    float64 m_DeltaT;                                   /* 控制周期 */
    float64 csModePara_dt_PanelUnfold_Start;            /* 相对入轨段计时开始的帆板展开过程开始时间 */
    SPhaseParamX csJPCPara_Param_PP[5][3];
    float64 csJPCPara_Mdf_as_PP;                        /* 推力器的加速度修正系数 */
    float64 csJPCPara_Mlf_t_R13;                        /* R13区喷气脉宽限幅 */
    float64 csJPCPara_theta_bp[5][3];                   /* 相平面参数角度阈值 θ_bpZR */
    float64 csJPCPara_w_bp[5][3];                       /* 相平面参数附加角速度 ω_bpZR */
    float64 csJPCPara_Torq[12][3];                      /* 各姿控推力器的三轴力矩 Thr[i].Torq */
    unint32 csJPCPara_FP_FJXYZ;                         /* 姿控耦合交叉控制标志（=0；不进行交叉控制；=1XY轴交叉控制；=2XZ轴交叉控制；=3YZ轴交叉控制）  */
    float64 csJPCPara_Mdf_as_ACReal;                    /* 姿控推力器的加速度实际修正系数  */
    unint32 csJPCPara_F_Assign[3+1][12][6];             /* 推力器分配 [推力器分组][每个推力器][+-六个方向] */
    float64 csJPCPara_as[2][3+1][6];                    /* 小推力加速度 [翻板展开前/后或其他][FU=0/1/2/3][as_pos_x/as_neg_x/as_pos_y/as_neg_y/as_pos_z/as_neg_z] */

} CS_AttCtrl_Propel;

#endif // __CS_ATTCTRL_PROPEL__
