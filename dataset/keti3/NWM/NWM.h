#ifndef NWM_H
#define NWM_H

#include "stdio.h"
#include "std_utils.h"
#include "std_bitop.h"
#include "std_tycvt.h"

#ifdef __GCC_COMPILED__
// #include "Fyq.h"
#endif

#ifdef __cplusplus
extern "C" {
#endif

// IP Headers
#include "CS_AttCtrl_Propel.h"
#include "CS_Ctrl_Att_Rate.h"
#include "CS_GyroData_Disposal.h"
#include "CS_Gyro_Att_Predict.h"
#include "CS_IRES_Attitude.h"
#include "CS_OrbitComputation.h"
#include "CS_PrecessionNutationCal.h"
#include "CS_Track_Atti.h"
#include "CS_TrgtAtt_EIM.h"
#include "CS_TrgtAtt_NWM_USU.h"
#include "ModeConvert_EIM.h"
#include "ModeConvert_SBM.h"

// 结构体定义
typedef struct {
    float64 t0;  // 使用的轨道参数的参考时刻
    float64 da0;  // t0时刻轨道拟平半长轴减去地球半径之后的值
    float64 ad;  // 拟平半长轴的一阶长期系数
    float64 i0;  // t0时刻拟平轨道倾角
    float64 omg0;  // t0时刻拟平升交点赤经
    float64 omg1;  // 拟平升交点赤经的一阶长期项系数
    float64 kesid;  // ξ_mean的一阶长期项系数
    float64 etad;  // η_mean的一阶长期项系数
    float64 w1;  // 拟平近地点幅角的一阶长期项系数
    float64 etam;  // ηm = -m2_ξ_mean/ω1，m2_ξ_mean为ξ_mean的二阶摄动系数
    float64 a;  // ξ_mean和η_mean的长周期变化幅值
    float64 beta;  // ξ_mean和η_mean的长周期变化相位
    float64 lmd0;  // t0时刻λ_mean的初值
    float64 lmd1;  // λ_mean的长期项系数
    float64 lmd2;  // λ_mean的二阶长期系数
    float64 lmdg;  // 格林尼治恒星时角
    float64 msun0;  // t0时刻的太阳平近点角
    float64 wsun;  // t0时刻太阳的近地点角
    float64 omgsun;  // t0时刻太阳的升交点赤经
    float64 UTC0;  // 星时计时零点相对 GPS 计时零点的时间间隔
    float64 qd[4];  // 岁差章动四元数，qJD[0]～qJD[2]为矢量部分，qJD[3]为标量部分
} OrbI_t;

typedef struct {
    float64 t0;  // 使用的轨道参数的参考时刻
    float64 da0;  // t0时刻轨道拟平半长轴减去地球半径之后的值
    float64 ad;  // 拟平半长轴的一阶长期系数
    float64 i0;  // t0时刻拟平轨道倾角
    float64 omg0;  // t0时刻拟平升交点赤经
    float64 omg1;  // 拟平升交点赤经的一阶长期项系数
    float64 kesid;  // ξ_mean的一阶长期项系数
    float64 etad;  // η_mean的一阶长期项系数
    float64 w1;  // 拟平近地点幅角的一阶长期项系数
    float64 etam;  // ηm = -m2_ξ_mean/ω1，m2_ξ_mean为ξ_mean的二阶摄动系数
    float64 a;  // ξ_mean和η_mean的长周期变化幅值
    float64 beta;  // ξ_mean和η_mean的长周期变化相位
    float64 lmd0;  // t0时刻λ_mean的初值
    float64 lmd1;  // λ_mean的长期项系数
    float64 lmd2;  // λ_mean的二阶长期系数
    float64 lmdg;  // 格林尼治恒星时角
    float64 msun0;  // t0时刻的太阳平近点角
    float64 wsun;  // t0时刻太阳的近地点角
    float64 omgsun;  // t0时刻太阳的升交点赤经
    float64 UTC0;  // 星时计时零点相对 GPS 计时零点的时间间隔
    float64 qd[4];  // 岁差章动四元数，qJD[0]～qJD[2]为矢量部分，qJD[3]为标量部分
} OrbG_t;

typedef struct {
    float64 t0;  // 使用的轨道参数的参考时刻
    float64 da0;  // t0时刻轨道拟平半长轴减去地球半径之后的值
    float64 ad;  // 拟平半长轴的一阶长期系数
    float64 i0;  // t0时刻拟平轨道倾角
    float64 omg0;  // t0时刻拟平升交点赤经
    float64 omg1;  // 拟平升交点赤经的一阶长期项系数
    float64 kesid;  // ξ_mean的一阶长期项系数
    float64 etad;  // η_mean的一阶长期项系数
    float64 w1;  // 拟平近地点幅角的一阶长期项系数
    float64 etam;  // ηm = -m2_ξ_mean/ω1，m2_ξ_mean为ξ_mean的二阶摄动系数
    float64 a;  // ξ_mean和η_mean的长周期变化幅值
    float64 beta;  // ξ_mean和η_mean的长周期变化相位
    float64 lmd0;  // t0时刻λ_mean的初值
    float64 lmd1;  // λ_mean的长期项系数
    float64 lmd2;  // λ_mean的二阶长期系数
    float64 lmdg;  // 格林尼治恒星时角
    float64 msun0;  // t0时刻的太阳平近点角
    float64 wsun;  // t0时刻太阳的近地点角
    float64 omgsun;  // t0时刻太阳的升交点赤经
    float64 UTC0;  // 星时计时零点相对 GPS 计时零点的时间间隔
    float64 qd[4];  // 岁差章动四元数，qJD[0]～qJD[2]为矢量部分，qJD[3]为标量部分
} Orb_t;

typedef struct {
    float64 a;  // 外推轨道六根数参数a
    float64 i;  // 外推轨道六根数参数i
    float64 e;  // 外推轨道六根数参数e
    float64 f;  // 外推轨道六根数参数f
    float64 u;  // 外推轨道六根数参数u
    float64 w;  // 外推轨道六根数参数ω
    float64 omg;  // 外推轨道六根数参数Ω
    float64 M;  // 外推轨道六根数参数M
    float64 pos[3];  // 惯性坐标系位置x/y/z
    float64 rate[3];  // 惯性坐标系速度x/y/z
    float64 w0;  // 计算的轨道角速度
    float64 r;  // 计算的地心距离
    float64 cosrou;  // 地心半张角余弦
    float64 us;  // 太阳星历计算的太阳轨道的幅角u
    float64 l1;  // 计算的经度及地心经度
    float64 l;  // 计算的经度及地理经度
    float64 delta;  // 计算的经度及地心纬度
    float64 ap;  // 计算的轨道平根数半长轴a
    float64 omgp;  // 计算的轨道平根数Ω
    float64 kesip;  // 计算的轨道平根数ξ
    float64 etap;  // 计算的轨道平根数η
    float64 lmdp;  // 计算的轨道平根数λ
    float64 ip;  // 计算的轨道平根数i
    float64 kesi;  // 计算的轨道根数ξ
    float64 eta;  // 计算的轨道根数η
    float64 lmd;  // 计算的轨道根数λ
    float64 sb[3];  // 本体太阳矢量
    float64 si[3];  // 太阳矢量在惯性系表示
    float64 so[3];  // 太阳矢量在轨道系表示
    float64 usun;  // 太阳轨道的幅角u
    float64 coi[3][3];  // 从惯性系到轨道系的姿态转移矩阵
    float64 VRe[3];  // 地心矢量在惯性系的表示
    float64 qoi[4];  // 从惯性系到轨道系的四元数
    float64 w0i[3];  // 考虑轨道进动的轨道系相对于惯性系J2000.0的角速度
    float64 lmdG;  // 计算的轨道根数λG
    float64 Cz_lmdG[3][3];  // 计算的轨道根数λG的转换矩阵
    unint32 F_OrbAbnorm;  // w0校验通过标志(0:未注入，1:通过)
} OrbOut_t;


// 全局变量声明
extern float64 wbi[3];  // 陀螺测量得到的星体三轴惯性角速度 [rad/s]
extern float64 deltG[3];  // 陀螺测量得到的星体三轴输出 [rad]
extern unint32 F_StopCtrl;  // 星上停控标志(0: 非停控，1: 停控) [--]
extern unint32 FUsing_gyro[9];  // 当前拍陀螺使用标志(0:不使用，1:使用) [--]
extern float64 deltGm[9];  // 陀螺i测量角度增量 [rad]
extern unint32 F_NoUseGroup;  // 本周期无定姿陀螺组标志（0有可用陀螺，1无可用陀螺） [--]
extern unint32 FS_AttD;  // 定姿方式标志(=0,陀螺红外定姿; =1,星敏陀螺定姿; =2,星敏无陀螺定姿，但陀螺引入开环定姿; =3,星敏无陀螺定姿，陀螺不引入开环定姿; =4,红外无陀螺定姿，陀螺不引入开环定姿) [--]
extern unint32 FP_ModeStopCtrl[14];  // 是否无陀螺组可用时停控(0: 不允许,1: 允许) [--]
extern unint32 WorkMode;  // 工作模式字 [--]
extern float64 Atti_ESG[3];  // 星体三轴姿态(地敏+陀螺) [rad]
extern float64 dAtti_ESG[3];  // 星体三轴姿态角速度(红外+陀螺) [rad/s]
extern float64 wbo_ESG[3];  // 红外陀螺确定本体相对轨道系的惯性角速度 [rad/s]
extern float64 Cbo_ESG[3][3];  // 红外陀螺估计的方向余弦阵（从轨道坐标系到本体坐标系） [--]
extern float64 w_ESG[3];  // 星体惯性角速度(红外陀螺) [rad/s]
extern float64 woi[3];  // 轨道进动的轨道系相对于惯性系J2000.0的角速度 [rad/s]
extern unint32 Seq_AttD[14];  // 定姿转序 [--]
extern float64 D0_ESCorr[3];  // 地敏估陀螺本体系三轴常值漂移 [rad/h]
extern float64 De_ESCorr[3];  // 地敏估陀螺本体系三轴指数漂移 [rad/h]
extern float64 Eb_i[2][3];  // 由红外i测量计算的地心矢量在本体系的表示 [s]
extern float64 Eb[3];  // 由红外测量计算的地心矢量在本体系的表示 [--]
extern float64 phi_i[2];  // 系统误差补偿后的（或无补偿处理的）红外地球敏感器i测量处理的滚动角 [--]
extern float64 theta_i[2];  // 系统误差补偿后的（或无补偿处理的）红外地球敏感器i测量处理的俯仰角 [--]
extern unint32 FV_ES[2];  // 红外有效性标志(0:无效，1:有效) [--]
extern unint32 FU_ES[2];  // 使用红外进行姿态修正标志(0:不使用，1:使用) [--]
extern float64 Em[2][3];  // 红外地球敏感器i测量的地心矢量在敏感器坐标系的表达 [--]
extern float64 Phi_ES;  // 由红外输出计算得到的滚动角 [rad]
extern float64 theta_ES;  // 由红外输出计算得到的俯仰角 [rad]
extern float64 dPhi_ES;  // 由红外输出计算得到的滚动角速度 [rad/s]
extern float64 dtheta_ES;  // 由红外输出计算得到的俯仰角速度 [rad/s]
extern float64 Timer_Mode[14];  // 模式运行计时器 [s]
extern unint32 CycleNum;  // 周期计数 [--]
extern unint32 FS[2];  // 红外i选取标志(0,不引入;1,引入) [--]
extern unint32 FHV_ES[2];  // 红外i的硬件有效性标志(0:无效，1:有效通讯成功且校验和正确), [--]
extern float64 S_Emz[2];  // 静态红外地球敏感器i的地心矢量z轴分量的符号 [--]
extern float64 Rate_c[3];  // 三轴姿态角速度控制误差 [--]
extern float64 w_Clp[3];  // 星体惯性角速度(闭环) [ωx_Clp,ωy_Clp,ωz_Clp] [rad/s]
extern float64 q_ESG[4];  // 惯性姿态四元数(红外) [--]
extern float64 Cbo_Clp[3][3];  // 定姿引入闭环的方向余弦阵（从轨道坐标系到本体坐标系） [--]
extern float64 Atti_Clp[3];  // 三轴姿态角(闭环) [rad]
extern float64 dAtti_Clp[3];  // 三轴姿态角速度(闭环) [rad/s]
extern float64 wbo_Clp[3];  // 星体相对轨道系的惯性角速度(闭环) [rad/s]
extern float64 q_STG[4];  // 惯性姿态四元数(星敏) [--]
extern float64 Atti_C[3];  // 三轴姿态角控制误差 [rad]
extern float64 w_STG[3];  // 星体惯性角速度(星敏陀螺) [ωx_STG, ωy_STG, ωz_STG] [rad/s]
extern float64 qbt[4];  // 四元数
extern unint32 FS_ModeProc[14];  // 模式处理标志 [--]
extern float64 Atti_AAM[3];  // 星体三轴姿态(全捕模式） [rad]
extern float64 dAtti_AAM[3];  // 星体三轴姿态角速度(全捕模式) [rad/s]
extern float64 w_AAM[3];  // 陀螺数据处理的输出 [rad/s]
extern float64 q_STDyn[4];  // 惯性姿态四元数(星敏无陀螺) [--]
extern float64 w_STDyn[3];  // 星体惯性角速度(星敏无陀螺) [ωx_STDyn,ωy_STDyn,ωz_STDyn] [rad/s]
extern float64 Atti_Ref[3];  // 三轴实时目标姿态角 [rad]
extern unint32 FP_BMC;  // 允许偏置动量控制标志(0:不允许，1: 允许) [--]
extern float64 qri[4];  // 参考系相对惯性系的目标四元数 [--]
extern float64 wri[3];  // 三轴实时目标惯性角速度 [rad/s]
extern float64 coi[3][3];  // 从惯性系到轨道系的姿态转移矩阵
extern unint32 FP_Qctrl[14];  // 四元数控制标志 [--]
extern float64 dAtti_Ref[3];  // 三轴实时目标姿态角速度 [rad/s]
extern float64 Atti_STG[3];  // 星体三轴姿态(星敏+陀螺) [rad]
extern float64 dAtti_STG[3];  // 星体三轴姿态角速度(星敏+陀螺) [rad/s]
extern float64 wbo_STG[3];  // 星敏陀螺确定本体相对轨道系的惯性角速度 [rad/s]
extern float64 Cbo_STG[3][3];  // 星敏陀螺估计的方向余弦阵（从轨道坐标系到本体坐标系） [--]
extern float64 Atti_STDyn[3];  // 星体三轴姿态(星敏无陀螺) [rad]
extern float64 dAtti_STDyn[3];  // 星体三轴姿态角速度(星敏无陀螺) [rad/s]
extern float64 wbo_STDyn[3];  // 星敏无陀螺确定本体相对轨道系的惯性角速度 [rad/s]
extern float64 Cbo_STDyn[3][3];  // 星敏无陀螺估计的方向余弦阵（从轨道坐标系到本体坐标系） [--]
extern float64 t[12];  // Thr[i].t 各姿控喷管本拍输出喷气脉宽 [--]
extern float64 a[3];  // 喷气三轴角加速度 [--]
extern float64 a2[3];  // 喷气三轴角加速度,仅用于推进系统故障诊断 [--]
extern float64 SumTn2[3];  // 负XYZ轴喷气总计脉宽，仅用于推力器故障诊断 [s]
extern float64 SumTp2[3];  // 正XYZ轴喷气总计脉宽，仅用于推力器故障诊断 [s]
extern float64 t_AC[12];  // Thr[i].t_AC 各轨控喷管输出喷气脉宽 [--]
extern unint32 F_st[3];  // 三轴喷气状态 [--]
extern float64 apn[3][2];  // 三正一斜。ThrGr.a_px ,ThrGr.a_nx ,ThrGr.a_py,ThrGr.a_ny,ThrGr.a_pz,ThrGr.a_nz [--]
extern float64 ThrGr[3];  // 姿控推力器的喷气脉宽 [s]
extern float64 mPhase_ThetaC_pst[3];  // 姿态角阀值,deg [--]
extern unint32 mPhase_Region[3];  // 相区,Zones [--]
extern unint32 F_Jet[3];  // F_Jetx,y,z [--]
extern float64 mPhase_FJB[3];  // 喷气状态,F_Jet [--]
extern unint32 F_AssignUse[12];  // 推力器i本周期产生的某轴的力矩标志 [--]
extern float64 SumTn[3];  // 负XYZ轴喷气总计脉宽 [s]
extern float64 SumTp[3];  // 正XYZ轴喷气总计脉宽 [s]
extern unint32 m_SubMode;  // 全捕子模式字 [--]
extern float64 dAtti_C[3];  // 三轴姿态角速度控制误差 [rad/s]
extern unint32 ID_Mass;  // 帆板展开标志（0：未展开，1：展开） [--]
extern unint32 FU_thrGr;  // 姿控发动机分组状态标志(0:主、备分支均不工作;1:姿控用主份推力器;2:姿控用备份推力器;3:姿控用主、备双份推力器) [--]
extern unint32 FJ[3];  // FJXY,XZ,YZ [--]
extern unint32 FP_RWorCMGC[14];  // RWorCMG控制标志(1:允许;0: 禁止) [--]
extern unint32 F_UldT;  // 喷气卸载标志(1: 喷气卸载,0: 不卸载) [--]
extern unint32 F_EarthAcq;  // 全捕模式进行地地或太地捕获标志标志,0太地捕获方式，1地地捕获方式 [--]
extern unint32 F_YawCapt;  // 太地捕获时允许转地球捕获标志 [--]
extern unint32 FP_GK_JetBack;  // 惯性定向/扫描结束后回正常模式的控制方式 [--]
extern unint32 SMODE;  // 各模式子模式字（全捕+其他） [--]
extern float64 Js_All[3][3];  // 当前选用的星体惯量矩阵 [--]
extern unint32 WorkMode_Lst;  // 工作模式字历史值 [--]
extern float64 StarTime;  // 当前周期的星时 [s]
extern float64 Atti_Trgt[3];  // 三轴目标姿态角 [rad]
extern float64 Tc;  // 控制周期 [s]
extern float64 t_next;  // 下一个周期的星时 [s]
extern unint32 F_qJDerr;  // 岁差章动四元数故障标志 [--]
extern float64 CPN[3][3];  // 岁差章动矩阵（从瞬时真赤惯性系到J2000系的转换矩阵） [--]
extern float64 qJD[4];  // 岁差章动四元数，qJD[0]～qJD[2]为矢量部分，qJD[3]为标量部分 [--]
extern unint32 FS_CPNCal;  // 岁差章动矩阵在轨计算标志（0:采用地面注入; 1:采用星上自主计算） [--]
extern unint32 F_TurnAAM;  // 允许转AAM标志（=0不允许；=1允许） [--]
extern unint32 FV;  // 轨道数据有效标志(0:无效，1:有效) [--]
extern unint32 F_SunlightZone[3];  // 阳照区标志（0地影区，1阳照区）[0]表示控制系统闭环使用的，对日巡航与对地定向的切换的阳照区标志[1]表示真实的阳照区；[2]表示总体特殊要求的阳照区，仅供遥测用；
extern unint32 FV_NoInsert;  // 轨道数据注入标志(0:未注入，1:有注入)
extern OrbI_t OrbI;  // 由地面注入的轨道外推参数 [--]
extern OrbG_t OrbG;  // 星上所使用的轨道外推参数 [--]
extern Orb_t Orb;  // 判断有效的GPS数据产生的轨道外推参数 [--]
extern OrbOut_t OrbOut;  // 环境计算所得的输出 [--]
extern unint32 FP_OrbUpdate[14];  // 轨道根数更新允许标志(1:允许;0: 禁止) [--]
extern unint32 F_DTOrbitEUpdate;  // 轨道根数，星时是否更新标志（=0系统不进行校时和19根数注入更新；=1系统正常校时和19根数注入） [--]
extern unint32 FP_UseOtherOrb;  // 允许使用其他轨道参数标志(=0,不允许; =1,允许) [--]
extern unint32 FP_WoPrecession;  // ωoi计算是否考虑轨道进动(0:不考虑; 1:考虑) [--]
extern unint32 FS_UseType;  // 是否引入GPS轨道计算(=0,轨道计算不引入GPS;=1,引入GPS通道板;=2,引入GPS轨道板)
extern float64 Cro[3][3];  // 从轨道坐标系到参考坐标系的方向余弦阵 [--]
extern float64 ddAtti_Ref[3];  // 三轴实时目标姿态角加速度 [rad/s2]
extern float64 TorqRef[3];  // 计算的期望前馈控制力矩 [Nm]
extern float64 A_Ref_si[3];  // 三轴视轴实时目标姿态角 [rad]
extern float64 Cro_si[3][3];  // 从惯性坐标系到参考坐标系的方向余弦阵
extern float64 wri_si[3];  // 视轴下的三轴实时目标惯性角速度
extern float64 psi_DA;  // 平滑后的实际偏流角 [rad]
extern float64 dpsi_DA;  // 平滑后的实际偏流角速度 [rad/s]
extern float64 tx_thrGr;  // X轴喷气脉宽 [s]
extern float64 ty_thrGr;  // Y轴喷气脉宽 [s]
extern float64 tz_thrGr;  // Z轴喷气脉宽 [s]
extern float64 t_thr[12];  // 姿控推力器的喷气脉宽 [s]
extern float64 wro[3];  // 从轨道坐标系到参考坐标系的角速度_x000d_
extern float64 Mlfw;  // 惯性角速度限幅 [rad/s]
extern float64 Vbs[9][3];  // 陀螺1-9的安装矩阵
extern float64 deltag_Lst[3];  // 陀螺测量得到的星体三轴输出历史值
extern float64 MlfA_ESG[3][14];  // 姿态估计的角度限幅阈值 [rad/s]
extern float64 LmtEm_ConstErr;  // Em常值检测阈值
extern float64 dt_ESUsed_EIM;  // 相对入轨段计时开始的引入红外姿态修正时间 [s]
extern unint32 FS_SCMType;  // 对日姿态计算方法 0：轨道相位法 1：矢量叉乘法 2：连续偏航
extern float64 dphi_Comps;  // 红外确定的本体系滚动姿态的偏差补偿量 [rad]
extern float64 dtheta_Comps;  // 红外确定的本体系俯仰姿态的偏差补偿量 [rad]
extern float64 dphib_Comps[2];  // 红外i的滚动角（卫星本体系）系统误差 [rad]
extern float64 dthetab_Comps[2];  // 红外i的俯仰角（卫星本体系）系统误差 [rad]
extern float64 CbsT[2][3][3];  // 红外i安装矩阵
extern float64 Mlf_D0;  // 陀螺常值漂移限幅值 [rad/h]
extern float64 Mlf_De;  // 陀螺指数漂移限幅值 [rad/h]
extern float64 Mdf_f_dphi;  // 红外组滚动/俯仰差分角速度（卫星本体系）的滤波系数1（历史值系数） [--]
extern float64 Mlf_dphi;  // 红外滤波修正算法中，红外组滚动轴修正新息限幅值（大于该阈值按照该限幅值进行修正） [rad]
extern float64 Mlf_dtheta;  // 红外滤波修正算法中，红外组俯仰轴修正新息限幅值（大于该阈值按照该限幅值进行修正） [rad]
extern float64 K_CorrDe_ESG[3];  // 红外姿态修正时进行陀螺三轴指数漂移修正系数 [--]
extern float64 K_Corrdphi_ESG[6];  // 红外姿态修正时根据滚动轴新息误差进行的修正系数 [--]
extern float64 K_Corrdtheta_ESG[3];  // 红外姿态修正时根据俯仰轴新息误差进行的修正系数 [--]
extern unint32 FP_IRESUse_AHM[14];  // 偏置飞行模式下是否允许红外参与姿态修正以及系统故障检测（=0不允许；=1允许） [--]
extern unint32 FP_ESProc[14];  // 允许红外特殊处理的标志（=0，不允许；=1时，表示允许）
extern unint32 LmtN_ConstErr;  // 红外原始测量（弦宽、前基或地心矢量）输出常值诊断次数，大于该阈值则红外无效 [--]
extern float64 Ts;  // 红外采样周期
extern unint32 ANTGr_LmtH_Num_dw;  // 姿态角速度差分求姿态角加速度的周期数保护上限 [--]
extern float64 as[2][4][6];  // 小推力加速度 [deg/s2]
extern unint32 F_Assign[4][12][6];  // 推力器分配表
extern float64 dt_PanelUnfold_Start;  // 相对入轨段初始时刻的帆板展开过程起始时间（不是相对于星箭分离时刻） [s]
extern Param_PP_t Param_PP[5][3];  // 相平面控制参数
extern float64 Mdf_as_PP;  // 姿控推力器的加速度修正系数（用于三轴相平面脉宽计算、推力器故障诊断、喷气安全底线时间判断） [--]
extern float64 Mlf_t_R13;  // R13区（步进区）内的三轴喷气最大脉宽限幅值（与Tc相同表示不限幅，挠性影响较大的卫星可以限制） [s]
extern float64 theta_bp[5][3];  // 相平面参数角度阈值 [deg]
extern float64 w_bp[5][3];  // 相平面参数附加角速度 [deg/s]
extern float64 Torq[12][3];  // 各姿控推力器的标称三轴力矩（采用无陀螺动力学定姿时，若卫星质心变化较大时，地面重新注入） [Nm]
extern unint32 FP_FJXYZ;  // 姿控耦合交叉控制标志（=0；不进行交叉控制；=1XY轴交叉控制；=2XZ轴交叉控制；=3YZ轴交叉控制） [--]
extern float64 Mdf_as_ACReal;  // 姿控推力器的加速度实际修正系数 [--]
extern float64 UTC0;  // 星时计时零点相对GPS计时零点的时间间隔 [s]
extern float64 tGPS0;  // GPS计时零点UTC相对于J2000.0（2000年1月1日12时0分0秒）的时间间隔（忽略跳秒） [s]
extern float64 dT_UTC2TDT;  // GPS计时零点UTC与TDT的时间差（=跳秒+32.184） [s]
extern unint32 Num_NoOrb;  // 轨道连续无效次数阈值
extern unint32 FS_NoOrbPro;  // 轨道无效处理标志
extern float64 calc_r_norm;  // 地心距离的正常值 [km]
extern float64 calc_w0_norm;  // 轨道角速度ω0的正常值 [rad/s]
extern float64 calc_cosrou_norm;  // cosρ的正常值 [--]
extern float64 calc_Lmt_dw0;  // 轨道角速度Orb.ω0的误差阈值 [rad/s]
extern float64 Lmt_dT;  // 轨道时间与当前星时误差阈值 [s]
extern float64 Mu;  // 引力常数
extern float64 Re;  // 地球赤道半径
extern float64 We;  // 地球自转角速度
extern float64 A2;  // 地球带谐项系数
extern float64 Hco2;  // 二氧化碳层距地面高度
extern float64 dMSun;  // 太阳轨道平近点角的变化率
extern float64 eSun;  // 太阳轨道的偏心率
extern float64 iSun;  // 太阳轨道的倾角
extern float64 Cbiasp[3][3];  // 姿态偏置矩阵
extern float64 Csib_DARot[3][3];  // 视轴坐标系转换矩阵sib
extern float64 Cbsi_DARot[3][3];  // 视轴坐标系转换矩阵bsit
extern float64 dt_OrbitInject;  // 星箭分离到入轨段计时开始的相对时间 [s]
extern float64 dt_END_EIM;  // 相对入轨段初始时刻的入轨段退出时间 [s]
extern float64 t0;  // 使用的轨道参数的参考时刻 [s]
extern float64 Mdf_TorqRef;  // 姿态机动前馈力矩的修正系数 [--]
extern float64 Mlf_TorqRef;  // 前馈力矩模的限幅，超过则力矩清零 [Nm]
// 其他函数声明
extern void ParaInit(void);
extern void ParaInput_AOCC2NWM(void);
extern void ParaOutput_NWM2AOCC(void);

// 初始化阶段
extern void NWMInit(void);
// 主循环
extern void NWMTask(void);
#ifdef __cplusplus
}
#endif
#endif