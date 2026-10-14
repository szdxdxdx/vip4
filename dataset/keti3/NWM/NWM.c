#include "NWM.h"

// 全局变量声明
float64 wbi[3];               // 陀螺测量得到的星体三轴惯性角速度 [rad/s]
float64 deltG[3];             // 陀螺测量得到的星体三轴输出 [rad]
unint32 F_StopCtrl;           // 星上停控标志(0: 非停控，1: 停控) [--]
unint32 FUsing_gyro[9];       // 当前拍陀螺使用标志(0:不使用，1:使用) [--]
float64 deltGm[9];            // 陀螺i测量角度增量 [rad]
unint32 F_NoUseGroup;         // 本周期无定姿陀螺组标志（0有可用陀螺，1无可用陀螺） [--]
unint32 FS_AttD;              // 定姿方式标志(=0,陀螺红外定姿; =1,星敏陀螺定姿; =2,星敏无陀螺定姿，但陀螺引入开环定姿; =3,星敏无陀螺定姿，陀螺不引入开环定姿; =4,红外无陀螺定姿，陀螺不引入开环定姿) [--]
unint32 FP_ModeStopCtrl[14];  // 是否无陀螺组可用时停控(0: 不允许,1: 允许) [--]
unint32 WorkMode;             // 工作模式字 [--]
float64 Atti_ESG[3];          // 星体三轴姿态(地敏+陀螺) [rad]
float64 dAtti_ESG[3];         // 星体三轴姿态角速度(红外+陀螺) [rad/s]
float64 wbo_ESG[3];           // 红外陀螺确定本体相对轨道系的惯性角速度 [rad/s]
float64 Cbo_ESG[3][3];        // 红外陀螺估计的方向余弦阵（从轨道坐标系到本体坐标系） [--]
float64 w_ESG[3];             // 星体惯性角速度(红外陀螺) [rad/s]
float64 woi[3];               // 轨道进动的轨道系相对于惯性系J2000.0的角速度 [rad/s]
unint32 Seq_AttD[14];         // 定姿转序 [--]
float64 D0_ESCorr[3];         // 地敏估陀螺本体系三轴常值漂移 [rad/h]
float64 De_ESCorr[3];         // 地敏估陀螺本体系三轴指数漂移 [rad/h]
float64 Eb_i[2][3];           // 由红外i测量计算的地心矢量在本体系的表示 [s]
float64 Eb[3];                // 由红外测量计算的地心矢量在本体系的表示 [--]
float64 phi_i[2];             // 系统误差补偿后的（或无补偿处理的）红外地球敏感器i测量处理的滚动角 [--]
float64 theta_i[2];           // 系统误差补偿后的（或无补偿处理的）红外地球敏感器i测量处理的俯仰角 [--]
unint32 FV_ES[2];             // 红外有效性标志(0:无效，1:有效) [--]
unint32 FU_ES[2];             // 使用红外进行姿态修正标志(0:不使用，1:使用) [--]
float64 Em[2][3];             // 红外地球敏感器i测量的地心矢量在敏感器坐标系的表达 [--]
float64 Phi_ES;               // 由红外输出计算得到的滚动角 [rad]
float64 theta_ES;             // 由红外输出计算得到的俯仰角 [rad]
float64 dPhi_ES;              // 由红外输出计算得到的滚动角速度 [rad/s]
float64 dtheta_ES;            // 由红外输出计算得到的俯仰角速度 [rad/s]
float64 Timer_Mode[14];       // 模式运行计时器 [s]
unint32 CycleNum;             // 周期计数 [--]
unint32 FS[2];                // 红外i选取标志(0,不引入;1,引入) [--]
unint32 FHV_ES[2];            // 红外i的硬件有效性标志(0:无效，1:有效通讯成功且校验和正确), [--]
float64 S_Emz[2];             // 静态红外地球敏感器i的地心矢量z轴分量的符号 [--]
float64 Rate_c[3];            // 三轴姿态角速度控制误差 [--]
float64 w_Clp[3];             // 星体惯性角速度(闭环) [ωx_Clp,ωy_Clp,ωz_Clp] [rad/s]
float64 q_ESG[4];             // 惯性姿态四元数(红外) [--]
float64 Cbo_Clp[3][3];        // 定姿引入闭环的方向余弦阵（从轨道坐标系到本体坐标系） [--]
float64 Atti_Clp[3];          // 三轴姿态角(闭环) [rad]
float64 dAtti_Clp[3];         // 三轴姿态角速度(闭环) [rad/s]
float64 wbo_Clp[3];           // 星体相对轨道系的惯性角速度(闭环) [rad/s]
float64 q_STG[4];             // 惯性姿态四元数(星敏) [--]
float64 Atti_C[3];            // 三轴姿态角控制误差 [rad]
float64 w_STG[3];             // 星体惯性角速度(星敏陀螺) [ωx_STG, ωy_STG, ωz_STG] [rad/s]
float64 qbt[4];               // 四元数
unint32 FS_ModeProc[14];      // 模式处理标志 [--]
float64 Atti_AAM[3];          // 星体三轴姿态(全捕模式） [rad]
float64 dAtti_AAM[3];         // 星体三轴姿态角速度(全捕模式) [rad/s]
float64 w_AAM[3];             // 陀螺数据处理的输出 [rad/s]
float64 q_STDyn[4];           // 惯性姿态四元数(星敏无陀螺) [--]
float64 w_STDyn[3];           // 星体惯性角速度(星敏无陀螺) [ωx_STDyn,ωy_STDyn,ωz_STDyn] [rad/s]
float64 Atti_Ref[3];          // 三轴实时目标姿态角 [rad]
unint32 FP_BMC;               // 允许偏置动量控制标志(0:不允许，1: 允许) [--]
float64 qri[4];               // 参考系相对惯性系的目标四元数 [--]
float64 wri[3];               // 三轴实时目标惯性角速度 [rad/s]
float64 coi[3][3];            // 从惯性系到轨道系的姿态转移矩阵
unint32 FP_Qctrl[14];         // 四元数控制标志 [--]
float64 dAtti_Ref[3];         // 三轴实时目标姿态角速度 [rad/s]
float64 Atti_STG[3];          // 星体三轴姿态(星敏+陀螺) [rad]
float64 dAtti_STG[3];         // 星体三轴姿态角速度(星敏+陀螺) [rad/s]
float64 wbo_STG[3];           // 星敏陀螺确定本体相对轨道系的惯性角速度 [rad/s]
float64 Cbo_STG[3][3];        // 星敏陀螺估计的方向余弦阵（从轨道坐标系到本体坐标系） [--]
float64 Atti_STDyn[3];        // 星体三轴姿态(星敏无陀螺) [rad]
float64 dAtti_STDyn[3];       // 星体三轴姿态角速度(星敏无陀螺) [rad/s]
float64 wbo_STDyn[3];         // 星敏无陀螺确定本体相对轨道系的惯性角速度 [rad/s]
float64 Cbo_STDyn[3][3];      // 星敏无陀螺估计的方向余弦阵（从轨道坐标系到本体坐标系） [--]
float64 t[12];                // Thr[i].t 各姿控喷管本拍输出喷气脉宽 [--]
float64 a[3];                 // 喷气三轴角加速度 [--]
float64 a2[3];                // 喷气三轴角加速度,仅用于推进系统故障诊断 [--]
float64 SumTn2[3];            // 负XYZ轴喷气总计脉宽，仅用于推力器故障诊断 [s]
float64 SumTp2[3];            // 正XYZ轴喷气总计脉宽，仅用于推力器故障诊断 [s]
float64 t_AC[12];             // Thr[i].t_AC 各轨控喷管输出喷气脉宽 [--]
unint32 F_st[3];              // 三轴喷气状态 [--]
float64 apn[3][2];            // 三正一斜。ThrGr.a_px ,ThrGr.a_nx ,ThrGr.a_py,ThrGr.a_ny,ThrGr.a_pz,ThrGr.a_nz [--]
float64 ThrGr[3];             // 姿控推力器的喷气脉宽 [s]
float64 mPhase_ThetaC_pst[3]; // 姿态角阀值,deg [--]
unint32 mPhase_Region[3];     // 相区,Zones [--]
unint32 F_Jet[3];             // F_Jetx,y,z [--]
float64 mPhase_FJB[3];        // 喷气状态,F_Jet [--]
unint32 F_AssignUse[12];      // 推力器i本周期产生的某轴的力矩标志 [--]
float64 SumTn[3];             // 负XYZ轴喷气总计脉宽 [s]
float64 SumTp[3];             // 正XYZ轴喷气总计脉宽 [s]
unint32 m_SubMode;            // 全捕子模式字 [--]
float64 dAtti_C[3];           // 三轴姿态角速度控制误差 [rad/s]
unint32 ID_Mass;              // 帆板展开标志（0：未展开，1：展开） [--]
unint32 FU_thrGr;             // 姿控发动机分组状态标志(0:主、备分支均不工作;1:姿控用主份推力器;2:姿控用备份推力器;3:姿控用主、备双份推力器) [--]
unint32 FJ[3];                // FJXY,XZ,YZ [--]
unint32 FP_RWorCMGC[14];      // RWorCMG控制标志(1:允许;0: 禁止) [--]
unint32 F_UldT;               // 喷气卸载标志(1: 喷气卸载,0: 不卸载) [--]
unint32 F_EarthAcq;           // 全捕模式进行地地或太地捕获标志标志,0太地捕获方式，1地地捕获方式 [--]
unint32 F_YawCapt;            // 太地捕获时允许转地球捕获标志 [--]
unint32 FP_GK_JetBack;        // 惯性定向/扫描结束后回正常模式的控制方式 [--]
unint32 SMODE;                // 各模式子模式字（全捕+其他） [--]
float64 Js_All[3][3];         // 当前选用的星体惯量矩阵 [--]
unint32 WorkMode_Lst;         // 工作模式字历史值 [--]
float64 StarTime;             // 当前周期的星时 [s]
float64 Atti_Trgt[3];         // 三轴目标姿态角 [rad]
float64 Tc;                   // 控制周期 [s]
float64 t_next;               // 下一个周期的星时 [s]
unint32 F_qJDerr;             // 岁差章动四元数故障标志 [--]
float64 CPN[3][3];            // 岁差章动矩阵（从瞬时真赤惯性系到J2000系的转换矩阵） [--]
float64 qJD[4];               // 岁差章动四元数，qJD[0]～qJD[2]为矢量部分，qJD[3]为标量部分 [--]
unint32 FS_CPNCal;            // 岁差章动矩阵在轨计算标志（0:采用地面注入; 1:采用星上自主计算） [--]
unint32 F_TurnAAM;            // 允许转AAM标志（=0不允许；=1允许） [--]
unint32 FV;                   // 轨道数据有效标志(0:无效，1:有效) [--]
unint32 F_SunlightZone[3];    // 阳照区标志（0地影区，1阳照区）[0]表示控制系统闭环使用的，对日巡航与对地定向的切换的阳照区标志[1]表示真实的阳照区；[2]表示总体特殊要求的阳照区，仅供遥测用；
unint32 FV_NoInsert;          // 轨道数据注入标志(0:未注入，1:有注入)
OrbI_t OrbI;                  // 由地面注入的轨道外推参数 [--]
OrbG_t OrbG;                  // 星上所使用的轨道外推参数 [--]
Orb_t Orb;                    // 判断有效的GPS数据产生的轨道外推参数 [--]
OrbOut_t OrbOut;              // 环境计算所得的输出 [--]
unint32 FP_OrbUpdate[14];     // 轨道根数更新允许标志(1:允许;0: 禁止) [--]
unint32 F_DTOrbitEUpdate;     // 轨道根数，星时是否更新标志（=0系统不进行校时和19根数注入更新；=1系统正常校时和19根数注入） [--]
unint32 FP_UseOtherOrb;       // 允许使用其他轨道参数标志(=0,不允许; =1,允许) [--]
unint32 FP_WoPrecession;      // ωoi计算是否考虑轨道进动(0:不考虑; 1:考虑) [--]
unint32 FS_UseType;           // 是否引入GPS轨道计算(=0,轨道计算不引入GPS;=1,引入GPS通道板;=2,引入GPS轨道板)
float64 Cro[3][3];            // 从轨道坐标系到参考坐标系的方向余弦阵 [--]
float64 ddAtti_Ref[3];        // 三轴实时目标姿态角加速度 [rad/s2]
float64 TorqRef[3];           // 计算的期望前馈控制力矩 [Nm]
float64 A_Ref_si[3];          // 三轴视轴实时目标姿态角 [rad]
float64 Cro_si[3][3];         // 从惯性坐标系到参考坐标系的方向余弦阵
float64 wri_si[3];            // 视轴下的三轴实时目标惯性角速度
float64 psi_DA;               // 平滑后的实际偏流角 [rad]
float64 dpsi_DA;              // 平滑后的实际偏流角速度 [rad/s]
float64 tx_thrGr;             // X轴喷气脉宽 [s]
float64 ty_thrGr;             // Y轴喷气脉宽 [s]
float64 tz_thrGr;             // Z轴喷气脉宽 [s]
float64 t_thr[12];            // 姿控推力器的喷气脉宽 [s]
float64 wro[3];               // 从轨道坐标系到参考坐标系的角速度_x000d_
float64 Mlfw;                 // 惯性角速度限幅 [rad/s]
float64 Vbs[9][3];            // 陀螺1-9的安装矩阵
float64 deltag_Lst[3];        // 陀螺测量得到的星体三轴输出历史值
float64 MlfA_ESG[3][14];      // 姿态估计的角度限幅阈值 [rad/s]
float64 LmtEm_ConstErr;       // Em常值检测阈值
float64 dt_ESUsed_EIM;        // 相对入轨段计时开始的引入红外姿态修正时间 [s]
unint32 FS_SCMType;           // 对日姿态计算方法 0：轨道相位法 1：矢量叉乘法 2：连续偏航
float64 dphi_Comps;           // 红外确定的本体系滚动姿态的偏差补偿量 [rad]
float64 dtheta_Comps;         // 红外确定的本体系俯仰姿态的偏差补偿量 [rad]
float64 dphib_Comps[2];       // 红外i的滚动角（卫星本体系）系统误差 [rad]
float64 dthetab_Comps[2];     // 红外i的俯仰角（卫星本体系）系统误差 [rad]
float64 CbsT[2][3][3];        // 红外i安装矩阵
float64 Mlf_D0;               // 陀螺常值漂移限幅值 [rad/h]
float64 Mlf_De;               // 陀螺指数漂移限幅值 [rad/h]
float64 Mdf_f_dphi;           // 红外组滚动/俯仰差分角速度（卫星本体系）的滤波系数1（历史值系数） [--]
float64 Mlf_dphi;             // 红外滤波修正算法中，红外组滚动轴修正新息限幅值（大于该阈值按照该限幅值进行修正） [rad]
float64 Mlf_dtheta;           // 红外滤波修正算法中，红外组俯仰轴修正新息限幅值（大于该阈值按照该限幅值进行修正） [rad]
float64 K_CorrDe_ESG[3];      // 红外姿态修正时进行陀螺三轴指数漂移修正系数 [--]
float64 K_Corrdphi_ESG[6];    // 红外姿态修正时根据滚动轴新息误差进行的修正系数 [--]
float64 K_Corrdtheta_ESG[3];  // 红外姿态修正时根据俯仰轴新息误差进行的修正系数 [--]
unint32 FP_IRESUse_AHM[14];   // 偏置飞行模式下是否允许红外参与姿态修正以及系统故障检测（=0不允许；=1允许） [--]
unint32 FP_ESProc[14];        // 允许红外特殊处理的标志（=0，不允许；=1时，表示允许）
unint32 LmtN_ConstErr;        // 红外原始测量（弦宽、前基或地心矢量）输出常值诊断次数，大于该阈值则红外无效 [--]
float64 Ts;                   // 红外采样周期
unint32 ANTGr_LmtH_Num_dw;    // 姿态角速度差分求姿态角加速度的周期数保护上限 [--]
float64 as[2][4][6];          // 小推力加速度 [deg/s2]
unint32 F_Assign[4][12][6];   // 推力器分配表
float64 dt_PanelUnfold_Start; // 相对入轨段初始时刻的帆板展开过程起始时间（不是相对于星箭分离时刻） [s]
Param_PP_t Param_PP[5][3];    // 相平面控制参数
float64 Mdf_as_PP;            // 姿控推力器的加速度修正系数（用于三轴相平面脉宽计算、推力器故障诊断、喷气安全底线时间判断） [--]
float64 Mlf_t_R13;            // R13区（步进区）内的三轴喷气最大脉宽限幅值（与Tc相同表示不限幅，挠性影响较大的卫星可以限制） [s]
float64 theta_bp[5][3];       // 相平面参数角度阈值 [deg]
float64 w_bp[5][3];           // 相平面参数附加角速度 [deg/s]
float64 Torq[12][3];          // 各姿控推力器的标称三轴力矩（采用无陀螺动力学定姿时，若卫星质心变化较大时，地面重新注入） [Nm]
unint32 FP_FJXYZ;             // 姿控耦合交叉控制标志（=0；不进行交叉控制；=1XY轴交叉控制；=2XZ轴交叉控制；=3YZ轴交叉控制） [--]
float64 Mdf_as_ACReal;        // 姿控推力器的加速度实际修正系数 [--]
float64 UTC0;                 // 星时计时零点相对GPS计时零点的时间间隔 [s]
float64 tGPS0;                // GPS计时零点UTC相对于J2000.0（2000年1月1日12时0分0秒）的时间间隔（忽略跳秒） [s]
float64 dT_UTC2TDT;           // GPS计时零点UTC与TDT的时间差（=跳秒+32.184） [s]
unint32 Num_NoOrb;            // 轨道连续无效次数阈值
unint32 FS_NoOrbPro;          // 轨道无效处理标志
float64 calc_r_norm;          // 地心距离的正常值 [km]
float64 calc_w0_norm;         // 轨道角速度ω0的正常值 [rad/s]
float64 calc_cosrou_norm;     // cosρ的正常值 [--]
float64 calc_Lmt_dw0;         // 轨道角速度Orb.ω0的误差阈值 [rad/s]
float64 Lmt_dT;               // 轨道时间与当前星时误差阈值 [s]
float64 Mu;                   // 引力常数
float64 Re;                   // 地球赤道半径
float64 We;                   // 地球自转角速度
float64 A2;                   // 地球带谐项系数
float64 Hco2;                 // 二氧化碳层距地面高度
float64 dMSun;                // 太阳轨道平近点角的变化率
float64 eSun;                 // 太阳轨道的偏心率
float64 iSun;                 // 太阳轨道的倾角
float64 Cbiasp[3][3];         // 姿态偏置矩阵
float64 Csib_DARot[3][3];     // 视轴坐标系转换矩阵sib
float64 Cbsi_DARot[3][3];     // 视轴坐标系转换矩阵bsit
float64 dt_OrbitInject;       // 星箭分离到入轨段计时开始的相对时间 [s]
float64 dt_END_EIM;           // 相对入轨段初始时刻的入轨段退出时间 [s]
float64 t0;                   // 使用的轨道参数的参考时刻 [s]
float64 Mdf_TorqRef;          // 姿态机动前馈力矩的修正系数 [--]
float64 Mlf_TorqRef;          // 前馈力矩模的限幅，超过则力矩清零 [Nm]

CS_GyroData_Disposal ipCS_GyroData_DisposalDetAtt1;
CS_Gyro_Att_Predict ipCS_Gyro_Att_PredictDetAtt2;
CS_IRES_Attitude ipCS_IRES_AttitudeDetAtt3;
CS_Ctrl_Att_Rate ipCS_Ctrl_Att_RateCalCtrl1;
CS_AttCtrl_Propel ipCS_AttCtrl_PropelCalCtrl2;

ModeConvert_EIM ipModeConvert_EIMSwitchMode11;
ModeConvert_SBM ipModeConvert_SBMSwitchMode12;

CS_PrecessionNutationCal ipCS_PrecessionNutationCalCalEnv1;
CS_OrbitComputation ipCS_OrbitComputationCalEnv2;
CS_TrgtAtt_EIM ipCS_TrgtAtt_EIMCalTar1;
CS_Track_Atti ipCS_Track_AttiCalTar2;
CS_TrgtAtt_NWM_USU ipCS_TrgtAtt_NWM_USUCalTar3;
CS_Track_Atti ipCS_Track_AttiCalTar4;
void NWMInit(void) {

  // Set StarTime  OrbI.t0;
  StarTime = OrbI.t0;

  // DetAtt1 - IP1: CS_GyroData_Disposal
  ipCS_GyroData_DisposalDetAtt1.fun = CS_GyroData_DisposalFun;
  ipCS_GyroData_DisposalDetAtt1.csGyroPara_Mlfw = Mlfw;
  Memcpyx((unint08 *)&ipCS_GyroData_DisposalDetAtt1.csGyroPara_Vbs[0][0], (unint08 *)&Vbs[0][0], sizeof(ipCS_GyroData_DisposalDetAtt1.csGyroPara_Vbs));
  Memsetx((unint08 *)&ipCS_GyroData_DisposalDetAtt1.csGyroData_deltag_Lst[0], 0x0, sizeof(ipCS_GyroData_DisposalDetAtt1.csGyroData_deltag_Lst));
  // DetAtt2 - IP1: CS_Gyro_Att_Predict
  ipCS_Gyro_Att_PredictDetAtt2.fun = CS_Gyro_Att_PredictFun;
  ipCS_Gyro_Att_PredictDetAtt2.csGyroPara_Mlfw = Mlfw;
  Memcpyx((unint08 *)&ipCS_Gyro_Att_PredictDetAtt2.csGyroPara_MlfA_ESG[0][0], (unint08 *)&MlfA_ESG[0][0], sizeof(ipCS_Gyro_Att_PredictDetAtt2.csGyroPara_MlfA_ESG));
  ipCS_Gyro_Att_PredictDetAtt2.m_DeltaT = Tc;
  // DetAtt3 - IP1: CS_IRES_Attitude
  ipCS_IRES_AttitudeDetAtt3.fun = CS_IRES_AttitudeFun;
  ipCS_IRES_AttitudeDetAtt3.m_DeltaT = Tc;
  ipCS_IRES_AttitudeDetAtt3.csModePara_dt_ESUsed_EIM = dt_ESUsed_EIM;
  ipCS_IRES_AttitudeDetAtt3.csPointSunPara_gfhSPAttCalcMode = FS_SCMType;
  ipCS_IRES_AttitudeDetAtt3.csIresPara_Ts = Ts;
  ipCS_IRES_AttitudeDetAtt3.csIresPara_dphi_Comps = dphi_Comps;
  ipCS_IRES_AttitudeDetAtt3.csIresPara_dtheta_Comps = dtheta_Comps;
  Memcpyx((unint08 *)&ipCS_IRES_AttitudeDetAtt3.csIresPara_dphib_Comps[0], (unint08 *)&dphib_Comps[0], sizeof(ipCS_IRES_AttitudeDetAtt3.csIresPara_dphib_Comps));
  Memcpyx((unint08 *)&ipCS_IRES_AttitudeDetAtt3.csIresPara_dthetab_Comps[0], (unint08 *)&dthetab_Comps[0], sizeof(ipCS_IRES_AttitudeDetAtt3.csIresPara_dthetab_Comps));
  Memcpyx((unint08 *)&ipCS_IRES_AttitudeDetAtt3.csIresPara_CbsT[0][0][0], (unint08 *)&CbsT[0][0][0], sizeof(ipCS_IRES_AttitudeDetAtt3.csIresPara_CbsT));
  ipCS_IRES_AttitudeDetAtt3.csGyroPara_Mlf_D0 = Mlf_D0;
  ipCS_IRES_AttitudeDetAtt3.csGyroPara_Mlf_De = Mlf_De;
  ipCS_IRES_AttitudeDetAtt3.csIresCorrPara_Mdf_f_dphi = Mdf_f_dphi;
  ipCS_IRES_AttitudeDetAtt3.csIresCorrPara_Mlf_dtheta = Mlf_dtheta;
  ipCS_IRES_AttitudeDetAtt3.csIresCorrPara_Mlf_dphi = Mlf_dphi;
  Memcpyx((unint08 *)&ipCS_IRES_AttitudeDetAtt3.csIresCorrPara_K_CorrDe_ESG[0], (unint08 *)&K_CorrDe_ESG[0], sizeof(ipCS_IRES_AttitudeDetAtt3.csIresCorrPara_K_CorrDe_ESG));
  Memcpyx((unint08 *)&ipCS_IRES_AttitudeDetAtt3.csIresCorrPara_K_Corrdphi_ESG[0], (unint08 *)&K_Corrdphi_ESG[0], sizeof(ipCS_IRES_AttitudeDetAtt3.csIresCorrPara_K_Corrdphi_ESG));
  Memcpyx((unint08 *)&ipCS_IRES_AttitudeDetAtt3.csIresCorrPara_K_Corrdtheta_ESG[0], (unint08 *)&K_Corrdtheta_ESG[0], sizeof(ipCS_IRES_AttitudeDetAtt3.csIresCorrPara_K_Corrdtheta_ESG));
  ipCS_IRES_AttitudeDetAtt3.csIresCorrPara_FP_IRESUse_AHM = 0;
  Memcpyx((unint08 *)&ipCS_IRES_AttitudeDetAtt3.csIresDiagPara_FP_ESProc[0], (unint08 *)&FP_ESProc[0], sizeof(ipCS_IRES_AttitudeDetAtt3.csIresDiagPara_FP_ESProc));
  ipCS_IRES_AttitudeDetAtt3.csIresDiagPara_LmtN_ConstErr = LmtN_ConstErr;
  ipCS_IRES_AttitudeDetAtt3.csIresDiagPara_LmtEm_ConstErr = LmtEm_ConstErr;
  Memsetx((unint08 *)&ipCS_IRES_AttitudeDetAtt3.csIresData_Cbs[0][0][0], 0x0, sizeof(ipCS_IRES_AttitudeDetAtt3.csIresData_Cbs));
  Memsetx((unint08 *)&ipCS_IRES_AttitudeDetAtt3.csIresDiagData_phi_i_Lst[0], 0x0, sizeof(ipCS_IRES_AttitudeDetAtt3.csIresDiagData_phi_i_Lst));
  Memsetx((unint08 *)&ipCS_IRES_AttitudeDetAtt3.csIresDiagData_theta_i_Lst[0], 0x0, sizeof(ipCS_IRES_AttitudeDetAtt3.csIresDiagData_theta_i_Lst));
  Memsetx((unint08 *)&ipCS_IRES_AttitudeDetAtt3.csIresDiagData_CntEmx_ConstErr[0], 0x0, sizeof(ipCS_IRES_AttitudeDetAtt3.csIresDiagData_CntEmx_ConstErr));
  Memsetx((unint08 *)&ipCS_IRES_AttitudeDetAtt3.csIresDiagData_CntEmy_ConstErr[0], 0x0, sizeof(ipCS_IRES_AttitudeDetAtt3.csIresDiagData_CntEmy_ConstErr));
  ipCS_IRES_AttitudeDetAtt3.csIresData_phi_Lst = 0;
  ipCS_IRES_AttitudeDetAtt3.csIresData_phi_Lst2 = 0;
  ipCS_IRES_AttitudeDetAtt3.csIresData_theta_Lst = 0;
  ipCS_IRES_AttitudeDetAtt3.csIresData_theta_Lst2 = 0;
  Memsetx((unint08 *)&ipCS_IRES_AttitudeDetAtt3.csIresDiagData_Em_Lst[0][0], 0x0, sizeof(ipCS_IRES_AttitudeDetAtt3.csIresDiagData_Em_Lst));
  // CalCtrl1 - IP1: CS_Ctrl_Att_Rate
  ipCS_Ctrl_Att_RateCalCtrl1.fun = CS_Ctrl_Att_RateFun;
  ipCS_Ctrl_Att_RateCalCtrl1.csAntPara_LmtH_Num_dw = ANTGr_LmtH_Num_dw;
  ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_angqbt_Lst = 0;
  Memsetx((unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_wbo_Lst[0][0], 0x0, sizeof(ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_wbo_Lst));
  Memsetx((unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_A_c_Lst[0], 0x0, sizeof(ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_A_c_Lst));
  // CalCtrl2 - IP1: CS_AttCtrl_Propel
  ipCS_AttCtrl_PropelCalCtrl2.fun = CS_AttCtrl_PropelFun;
  ipCS_AttCtrl_PropelCalCtrl2.csModePara_dt_PanelUnfold_Start = dt_PanelUnfold_Start;
  ipCS_AttCtrl_PropelCalCtrl2.m_DeltaT = Tc;
  Memsetx((unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCPara_Param_PP_ThetaD[0][0], 0x0, sizeof(ipCS_AttCtrl_PropelCalCtrl2.csJPCPara_Param_PP_ThetaD));
  Memsetx((unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCPara_Param_PP_ThetaB[0][0], 0x0, sizeof(ipCS_AttCtrl_PropelCalCtrl2.csJPCPara_Param_PP_ThetaB));
  Memsetx((unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCPara_Param_PP_Dtheta[0][0], 0x0, sizeof(ipCS_AttCtrl_PropelCalCtrl2.csJPCPara_Param_PP_Dtheta));
  Memsetx((unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCPara_Param_PP_ThetaV[0][0], 0x0, sizeof(ipCS_AttCtrl_PropelCalCtrl2.csJPCPara_Param_PP_ThetaV));
  Memcpyx((unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCPara_Param_PP_dThetaS[0][0], (unint08 *)&w_bp[0][0], sizeof(ipCS_AttCtrl_PropelCalCtrl2.csJPCPara_Param_PP_dThetaS));
  Memcpyx((unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCPara_Param_PP_dThetaV[0][0], (unint08 *)&w_bp[0][0], sizeof(ipCS_AttCtrl_PropelCalCtrl2.csJPCPara_Param_PP_dThetaV));
  Memsetx((unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCPara_Param_PP_dThetaL[0][0], 0x0, sizeof(ipCS_AttCtrl_PropelCalCtrl2.csJPCPara_Param_PP_dThetaL));
  Memsetx((unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCPara_Param_PP_dThetaLL[0][0], 0x0, sizeof(ipCS_AttCtrl_PropelCalCtrl2.csJPCPara_Param_PP_dThetaLL));
  Memsetx((unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCPara_Param_PP_Kj1[0][0], 0x0, sizeof(ipCS_AttCtrl_PropelCalCtrl2.csJPCPara_Param_PP_Kj1));
  Memsetx((unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCPara_Param_PP_Kj2[0][0], 0x0, sizeof(ipCS_AttCtrl_PropelCalCtrl2.csJPCPara_Param_PP_Kj2));
  Memsetx((unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCPara_Param_PP_KJ[0][0], 0x0, sizeof(ipCS_AttCtrl_PropelCalCtrl2.csJPCPara_Param_PP_KJ));
  Memsetx((unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCPara_Param_PP_Tmax[0][0], 0x0, sizeof(ipCS_AttCtrl_PropelCalCtrl2.csJPCPara_Param_PP_Tmax));
  Memsetx((unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCPara_Param_PP_Tmin[0][0], 0x0, sizeof(ipCS_AttCtrl_PropelCalCtrl2.csJPCPara_Param_PP_Tmin));
  ipCS_AttCtrl_PropelCalCtrl2.csJPCPara_Mdf_as_PP = Mdf_as_PP;
  ipCS_AttCtrl_PropelCalCtrl2.csJPCPara_Mlf_t_R13 = Mlf_t_R13;
  Memcpyx((unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCPara_theta_bp[0][0], (unint08 *)&theta_bp[0][0], sizeof(ipCS_AttCtrl_PropelCalCtrl2.csJPCPara_theta_bp));
  Memcpyx((unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCPara_w_bp[0][0], (unint08 *)&w_bp[0][0], sizeof(ipCS_AttCtrl_PropelCalCtrl2.csJPCPara_w_bp));
  Memcpyx((unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCPara_Torq[0][0], (unint08 *)&Torq[0][0], sizeof(ipCS_AttCtrl_PropelCalCtrl2.csJPCPara_Torq));
  ipCS_AttCtrl_PropelCalCtrl2.CsJPCPara_FP_FJXYZ = FP_FJXYZ;
  ipCS_AttCtrl_PropelCalCtrl2.csJPCPara_Mdf_as_ACReal = Mdf_as_ACReal;
  Memcpyx((unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCPara_as[0][0][0], (unint08 *)&as[0][0][0], sizeof(ipCS_AttCtrl_PropelCalCtrl2.csJPCPara_as));
  Memcpyx((unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCPara_F_Assign[0][0][0], (unint08 *)&F_Assign[0][0][0], sizeof(ipCS_AttCtrl_PropelCalCtrl2.csJPCPara_F_Assign));

  // SwitchMode1 - IP1: ModeConvert_EIM
  ipModeConvert_EIMSwitchMode11.fun = ModeConvert_EIMFun;
  ipModeConvert_EIMSwitchMode11.csModePara_dt_END_EIM = dt_END_EIM;

  // SwitchMode1 - IP2: ModeConvert_SBM
  ipModeConvert_SBMSwitchMode12.fun = ModeConvert_SBMFun;
  ipModeConvert_SBMSwitchMode12.csModePara_dt_OrbitInject = dt_OrbitInject;
  ipModeConvert_SBMSwitchMode12.csOrb19_Para_I_t0 = t0;

  // CalEnv1 - IP1: CS_PrecessionNutationCal
  ipCS_PrecessionNutationCalCalEnv1.fun = CS_PrecessionNutationCalFun;
  ipCS_PrecessionNutationCalCalEnv1.csOrb19_Para_I_UTC0 = UTC0;
  ipCS_PrecessionNutationCalCalEnv1.csGpsPara_tGPS0 = tGPS0;
  ipCS_PrecessionNutationCalCalEnv1.csGpsPara_dT_UTC2TDT = dT_UTC2TDT;
  // CalEnv2 - IP1: CS_OrbitComputation
  ipCS_OrbitComputationCalEnv2.fun = CS_OrbitComputationFun;
  ipCS_OrbitComputationCalEnv2.csOrbInjChkPara_calc_r_norm = calc_r_norm;
  ipCS_OrbitComputationCalEnv2.csOrbInjChkPara_calc_w0_norm = calc_w0_norm;
  ipCS_OrbitComputationCalEnv2.csOrbInjChkPara_calc_cosp_norm = calc_cosrou_norm;
  ipCS_OrbitComputationCalEnv2.csOrbInjChkPara_calc_Lmt_dw0 = calc_Lmt_dw0;
  ipCS_OrbitComputationCalEnv2.csOrbInjChkPara_Lmt_dT = Lmt_dT;
  ipCS_OrbitComputationCalEnv2.pOCP_Mu = Mu;
  ipCS_OrbitComputationCalEnv2.pOCP_Re = Re;
  ipCS_OrbitComputationCalEnv2.pOCP_We = We;
  ipCS_OrbitComputationCalEnv2.pOCP_A2 = A2;
  ipCS_OrbitComputationCalEnv2.pOCP_Hco2 = Hco2;
  ipCS_OrbitComputationCalEnv2.pOCP_dMSun = dMSun;
  ipCS_OrbitComputationCalEnv2.pOCP_eSun = eSun;
  ipCS_OrbitComputationCalEnv2.pOCP_iSun = iSun;
  ipCS_OrbitComputationCalEnv2.csOrbitErrJPara_Num_NoOrb = Num_NoOrb;
  ipCS_OrbitComputationCalEnv2.csOrbitErrJPara_FS_NoOrbPro = FS_NoOrbPro;
  ipCS_OrbitComputationCalEnv2.pOrbPara_t0 = 0;
  ipCS_OrbitComputationCalEnv2.pOrbPara_deltaa0 = 0;
  ipCS_OrbitComputationCalEnv2.pOrbPara_adelta = 0;
  ipCS_OrbitComputationCalEnv2.pOrbPara_i0 = 0;
  ipCS_OrbitComputationCalEnv2.pOrbPara_omg0 = 0;
  ipCS_OrbitComputationCalEnv2.pOrbPara_omg1 = 0;
  ipCS_OrbitComputationCalEnv2.pOrbPara_kesid = 0;
  ipCS_OrbitComputationCalEnv2.pOrbPara_etad = 0;
  ipCS_OrbitComputationCalEnv2.pOrbPara_w1 = 0;
  ipCS_OrbitComputationCalEnv2.pOrbPara_etam = 0;
  ipCS_OrbitComputationCalEnv2.pOrbPara_a = 0;
  ipCS_OrbitComputationCalEnv2.pOrbPara_beta = 0;
  ipCS_OrbitComputationCalEnv2.pOrbPara_lmd0 = 0;
  ipCS_OrbitComputationCalEnv2.pOrbPara_lmd1 = 0;
  ipCS_OrbitComputationCalEnv2.pOrbPara_lmd2 = 0;
  ipCS_OrbitComputationCalEnv2.pOrbPara_lmdg = 0;
  ipCS_OrbitComputationCalEnv2.csOrbitErrJData_Cnt_NoOrb = 0;
  // CalTar1 - IP1: CS_TrgtAtt_EIM
  ipCS_TrgtAtt_EIMCalTar1.fun = CS_TrgtAtt_EIMFun;
  Memcpyx((unint08 *)&ipCS_TrgtAtt_EIMCalTar1.csAttCoreData_Cbiasp[0][0], (unint08 *)&Cbiasp[0][0], sizeof(ipCS_TrgtAtt_EIMCalTar1.csAttCoreData_Cbiasp));
  // CalTar2 - IP1: CS_Track_Atti
  ipCS_Track_AttiCalTar2.fun = CS_Track_AttiFun;
  ipCS_Track_AttiCalTar2.m_DeltaT = Tc;
  ipCS_Track_AttiCalTar2.csCtrlerOtherPara_Mdf_TorqRef = Mdf_TorqRef;
  ipCS_Track_AttiCalTar2.csCtrlerOtherPara_Mlf_TorqRef = Mlf_TorqRef;
  Memcpyx((unint08 *)&ipCS_Track_AttiCalTar2.csCtrlerData_Js_Use[0][0], (unint08 *)&Js_All[0][0], sizeof(ipCS_Track_AttiCalTar2.csCtrlerData_Js_Use));
  Memsetx((unint08 *)&ipCS_Track_AttiCalTar2.csMnvData_dA_Ref_Lst[0], 0x0, sizeof(ipCS_Track_AttiCalTar2.csMnvData_dA_Ref_Lst));
  Memsetx((unint08 *)&ipCS_Track_AttiCalTar2.csAttCoreData_wri_Lst[0], 0x0, sizeof(ipCS_Track_AttiCalTar2.csAttCoreData_wri_Lst));
  // CalTar3 - IP1: CS_TrgtAtt_NWM_USU
  ipCS_TrgtAtt_NWM_USUCalTar3.fun = CS_TrgtAtt_NWM_USUFun;
  Memcpyx((unint08 *)&ipCS_TrgtAtt_NWM_USUCalTar3.csAttCoreData_Cbiasp[0][0], (unint08 *)&Cbiasp[0][0], sizeof(ipCS_TrgtAtt_NWM_USUCalTar3.csAttCoreData_Cbiasp));
  Memcpyx((unint08 *)&ipCS_TrgtAtt_NWM_USUCalTar3.csLoadAxisData_Csib_DARot[0][0], (unint08 *)&Cbsi_DARot[0][0], sizeof(ipCS_TrgtAtt_NWM_USUCalTar3.csLoadAxisData_Csib_DARot));
  Memcpyx((unint08 *)&ipCS_TrgtAtt_NWM_USUCalTar3.csLoadAxisData_Cbsi_DARot[0][0], (unint08 *)&Cbsi_DARot[0][0], sizeof(ipCS_TrgtAtt_NWM_USUCalTar3.csLoadAxisData_Cbsi_DARot));
  // CalTar4 - IP1: CS_Track_Atti
  ipCS_Track_AttiCalTar4.fun = CS_Track_AttiFun;
  ipCS_Track_AttiCalTar4.m_DeltaT = Tc;
  ipCS_Track_AttiCalTar4.csCtrlerOtherPara_Mdf_TorqRef = Mdf_TorqRef;
  ipCS_Track_AttiCalTar4.csCtrlerOtherPara_Mlf_TorqRef = Mlf_TorqRef;
  Memcpyx((unint08 *)&ipCS_Track_AttiCalTar4.csCtrlerData_Js_Use[0][0], (unint08 *)&Js_All[0][0], sizeof(ipCS_Track_AttiCalTar4.csCtrlerData_Js_Use));
  Memsetx((unint08 *)&ipCS_Track_AttiCalTar4.csMnvData_dA_Ref_Lst[0], 0x0, sizeof(ipCS_Track_AttiCalTar4.csMnvData_dA_Ref_Lst));
  Memsetx((unint08 *)&ipCS_Track_AttiCalTar4.csAttCoreData_wri_Lst[0], 0x0, sizeof(ipCS_Track_AttiCalTar4.csAttCoreData_wri_Lst));
  return;
}
void NWMTask(void) {

  // Set StarTime StarTime + Tc;
  StarTime = StarTime + Tc;
  // Set tx_thrGr 0.0;
  tx_thrGr = 0.0;
  // Set ty_thrGr 0.0;
  ty_thrGr = 0.0;
  // Set tz_thrGr 0.0;
  tz_thrGr = 0.0;
  // Set  t_thr  {0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0} ;
  t_thr[0] = 0.0;
  t_thr[1] = 0.0;
  t_thr[2] = 0.0;
  t_thr[3] = 0.0;
  t_thr[4] = 0.0;
  t_thr[5] = 0.0;
  t_thr[6] = 0.0;
  t_thr[7] = 0.0;
  t_thr[8] = 0.0;
  t_thr[9] = 0.0;
  t_thr[10] = 0.0;
  t_thr[11] = 0.0;
  if (WorkMode_Lst != 0x00u) {
    // IP1: CS_GyroData_Disposal - 输入参数赋值
    ipCS_GyroData_DisposalDetAtt1.csGyroDiagData_F_NoUseGroup = F_NoUseGroup;
    ipCS_GyroData_DisposalDetAtt1.csAttPara_FS_AttD = FS_AttD;
    Memcpyx((unint08 *)&ipCS_GyroData_DisposalDetAtt1.csGyroDiagPara_FP_ModeStopCtrl[0], (unint08 *)&FP_ModeStopCtrl[0], sizeof(ipCS_GyroData_DisposalDetAtt1.csGyroDiagPara_FP_ModeStopCtrl));
    Memcpyx((unint08 *)&ipCS_GyroData_DisposalDetAtt1.csGyroDiagData_FU_ing[0], (unint08 *)&FUsing_gyro[0], sizeof(ipCS_GyroData_DisposalDetAtt1.csGyroDiagData_FU_ing));
    Memcpyx((unint08 *)&ipCS_GyroData_DisposalDetAtt1.csGyroData_deltagm[0], (unint08 *)&deltGm[0], sizeof(ipCS_GyroData_DisposalDetAtt1.csGyroData_deltagm));
    ipCS_GyroData_DisposalDetAtt1.m_WorkMode = WorkMode;
    IPCALL(ipCS_GyroData_DisposalDetAtt1);
    // IP1: CS_GyroData_Disposal - 输出变量赋值
    Memcpyx((unint08 *)&deltG[0], (unint08 *)&ipCS_GyroData_DisposalDetAtt1.csGyroData_deltag[0], sizeof(deltG));
    Memcpyx((unint08 *)&wbi[0], (unint08 *)&ipCS_GyroData_DisposalDetAtt1.csGyroData_wbi[0], sizeof(wbi));
    F_StopCtrl = ipCS_GyroData_DisposalDetAtt1.csModeData_F_StopCtrl;

    // IP1: CS_Gyro_Att_Predict - 输入参数赋值
    Memcpyx((unint08 *)&ipCS_Gyro_Att_PredictDetAtt2.csGyroData_deltag[0], (unint08 *)&deltG[0], sizeof(ipCS_Gyro_Att_PredictDetAtt2.csGyroData_deltag));
    Memcpyx((unint08 *)&ipCS_Gyro_Att_PredictDetAtt2.csGyroData_D0_ESCorr[0], (unint08 *)&D0_ESCorr[0], sizeof(ipCS_Gyro_Att_PredictDetAtt2.csGyroData_D0_ESCorr));
    Memcpyx((unint08 *)&ipCS_Gyro_Att_PredictDetAtt2.csGyroData_De_ESCorr[0], (unint08 *)&De_ESCorr[0], sizeof(ipCS_Gyro_Att_PredictDetAtt2.csGyroData_De_ESCorr));
    Memcpyx((unint08 *)&ipCS_Gyro_Att_PredictDetAtt2.csOrbData_w0i[0], (unint08 *)&woi[0], sizeof(ipCS_Gyro_Att_PredictDetAtt2.csOrbData_w0i));
    ipCS_Gyro_Att_PredictDetAtt2.m_WorkMode = WorkMode;
    Memcpyx((unint08 *)&ipCS_Gyro_Att_PredictDetAtt2.csAttPara_Seq_AttD[0], (unint08 *)&Seq_AttD[0], sizeof(ipCS_Gyro_Att_PredictDetAtt2.csAttPara_Seq_AttD));
    Memcpyx((unint08 *)&ipCS_Gyro_Att_PredictDetAtt2.csAttCoreData_A_ESG[0], (unint08 *)&Atti_ESG[0], sizeof(ipCS_Gyro_Att_PredictDetAtt2.csAttCoreData_A_ESG));
    IPCALL(ipCS_Gyro_Att_PredictDetAtt2);
    // IP1: CS_Gyro_Att_Predict - 输出变量赋值
    Memcpyx((unint08 *)&Atti_ESG[0], (unint08 *)&ipCS_Gyro_Att_PredictDetAtt2.csAttCoreData_A_ESG[0], sizeof(Atti_ESG));
    Memcpyx((unint08 *)&dAtti_ESG[0], (unint08 *)&ipCS_Gyro_Att_PredictDetAtt2.csAttCoreData_Rate_ESG[0], sizeof(dAtti_ESG));
    Memcpyx((unint08 *)&wbo_ESG[0], (unint08 *)&ipCS_Gyro_Att_PredictDetAtt2.csAttCoreData_wbo_ESG[0], sizeof(wbo_ESG));
    Memcpyx((unint08 *)&Cbo_ESG[0][0], (unint08 *)&ipCS_Gyro_Att_PredictDetAtt2.csAttCoreData_Cbo_ESG[0][0], sizeof(Cbo_ESG));
    Memcpyx((unint08 *)&w_ESG[0], (unint08 *)&ipCS_Gyro_Att_PredictDetAtt2.csAttCoreData_w_ESG[0], sizeof(w_ESG));

    // IP1: CS_IRES_Attitude - 输入参数赋值
    ipCS_IRES_AttitudeDetAtt3.m_WorkMode = WorkMode;
    Memcpyx((unint08 *)&ipCS_IRES_AttitudeDetAtt3.ModeObjectTimer_Mode[0], (unint08 *)&Timer_Mode[0], sizeof(ipCS_IRES_AttitudeDetAtt3.ModeObjectTimer_Mode));
    ipCS_IRES_AttitudeDetAtt3.csAttPara_FS_AttD = FS_AttD;
    ipCS_IRES_AttitudeDetAtt3.csModeData_CycleNum = CycleNum;
    Memcpyx((unint08 *)&ipCS_IRES_AttitudeDetAtt3.csIresPara_FS[0], (unint08 *)&FS[0], sizeof(ipCS_IRES_AttitudeDetAtt3.csIresPara_FS));
    Memcpyx((unint08 *)&ipCS_IRES_AttitudeDetAtt3.csIresData_FHV[0], (unint08 *)&FHV_ES[0], sizeof(ipCS_IRES_AttitudeDetAtt3.csIresData_FHV));
    Memcpyx((unint08 *)&ipCS_IRES_AttitudeDetAtt3.csIresData_S_Emz[0], (unint08 *)&S_Emz[0], sizeof(ipCS_IRES_AttitudeDetAtt3.csIresData_S_Emz));
    ipCS_IRES_AttitudeDetAtt3.csIresData_dTheta = dtheta_ES;
    Memcpyx((unint08 *)&ipCS_IRES_AttitudeDetAtt3.csIresDiagData_FU[0], (unint08 *)&FU_ES[0], sizeof(ipCS_IRES_AttitudeDetAtt3.csIresDiagData_FU));
    Memcpyx((unint08 *)&ipCS_IRES_AttitudeDetAtt3.csIresDiagData_Em[0][0], (unint08 *)&Em[0][0], sizeof(ipCS_IRES_AttitudeDetAtt3.csIresDiagData_Em));
    ipCS_IRES_AttitudeDetAtt3.csIresData_phi = Phi_ES;
    ipCS_IRES_AttitudeDetAtt3.csIresData_theta = theta_ES;
    ipCS_IRES_AttitudeDetAtt3.csIresData_dPhi = dPhi_ES;
    Memcpyx((unint08 *)&ipCS_IRES_AttitudeDetAtt3.csAttCoreData_A_ESG[0], (unint08 *)&Atti_ESG[0], sizeof(ipCS_IRES_AttitudeDetAtt3.csAttCoreData_A_ESG));
    Memcpyx((unint08 *)&ipCS_IRES_AttitudeDetAtt3.csGyroData_D0_ESCorr[0], (unint08 *)&D0_ESCorr[0], sizeof(ipCS_IRES_AttitudeDetAtt3.csGyroData_D0_ESCorr));
    Memcpyx((unint08 *)&ipCS_IRES_AttitudeDetAtt3.csGyroData_De_ESCorr[0], (unint08 *)&De_ESCorr[0], sizeof(ipCS_IRES_AttitudeDetAtt3.csGyroData_De_ESCorr));
    IPCALL(ipCS_IRES_AttitudeDetAtt3);
    // IP1: CS_IRES_Attitude - 输出变量赋值
    Memcpyx((unint08 *)&Eb_i[0][0], (unint08 *)&ipCS_IRES_AttitudeDetAtt3.csIresDiagData_Eb_i[0][0], sizeof(Eb_i));
    Memcpyx((unint08 *)&Eb[0], (unint08 *)&ipCS_IRES_AttitudeDetAtt3.csGyroData_De_ESCorr[0], sizeof(Eb));
    Memcpyx((unint08 *)&phi_i[0], (unint08 *)&ipCS_IRES_AttitudeDetAtt3.csIresDiagData_phi_i[0], sizeof(phi_i));
    Memcpyx((unint08 *)&theta_i[0], (unint08 *)&ipCS_IRES_AttitudeDetAtt3.csIresDiagData_theta_i[0], sizeof(theta_i));
    Memcpyx((unint08 *)&FV_ES[0], (unint08 *)&ipCS_IRES_AttitudeDetAtt3.csIresDiagData_FV[0], sizeof(FV_ES));
    Memcpyx((unint08 *)&FU_ES[0], (unint08 *)&ipCS_IRES_AttitudeDetAtt3.csIresDiagData_FU[0], sizeof(FU_ES));
    Memcpyx((unint08 *)&Em[0][0], (unint08 *)&ipCS_IRES_AttitudeDetAtt3.csIresDiagData_Em[0][0], sizeof(Em));
    Phi_ES = ipCS_IRES_AttitudeDetAtt3.csIresData_phi;
    theta_ES = ipCS_IRES_AttitudeDetAtt3.csIresData_theta;
    dPhi_ES = ipCS_IRES_AttitudeDetAtt3.csIresData_dPhi;
    dtheta_ES = ipCS_IRES_AttitudeDetAtt3.csIresData_dTheta;
    Memcpyx((unint08 *)&Atti_ESG[0], (unint08 *)&ipCS_IRES_AttitudeDetAtt3.csAttCoreData_A_ESG[0], sizeof(Atti_ESG));
    Memcpyx((unint08 *)&D0_ESCorr[0], (unint08 *)&ipCS_IRES_AttitudeDetAtt3.csGyroData_D0_ESCorr[0], sizeof(D0_ESCorr));
    Memcpyx((unint08 *)&De_ESCorr[0], (unint08 *)&ipCS_IRES_AttitudeDetAtt3.csGyroData_De_ESCorr[0], sizeof(De_ESCorr));

    // IP1: CS_Ctrl_Att_Rate - 输入参数赋值
    ipCS_Ctrl_Att_RateCalCtrl1.m_WorkMode = WorkMode;
    Memcpyx((unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csCtrlerOtherPara_FS_ModeProc[0], (unint08 *)&FS_ModeProc[0], sizeof(ipCS_Ctrl_Att_RateCalCtrl1.csCtrlerOtherPara_FS_ModeProc));
    Memcpyx((unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csSGAttAcqData_A[0], (unint08 *)&Atti_AAM[0], sizeof(ipCS_Ctrl_Att_RateCalCtrl1.csSGAttAcqData_A));
    Memcpyx((unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csSGAttAcqData_dA[0], (unint08 *)&dAtti_AAM[0], sizeof(ipCS_Ctrl_Att_RateCalCtrl1.csSGAttAcqData_dA));
    Memcpyx((unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csSGAttAcqData_w[0], (unint08 *)&w_AAM[0], sizeof(ipCS_Ctrl_Att_RateCalCtrl1.csSGAttAcqData_w));
    ipCS_Ctrl_Att_RateCalCtrl1.csAttPara_FS_AttD = FS_AttD;
    Memcpyx((unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_q_STDyn[0], (unint08 *)&q_STDyn[0], sizeof(ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_q_STDyn));
    Memcpyx((unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_w_STDyn[0], (unint08 *)&w_STDyn[0], sizeof(ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_w_STDyn));
    ipCS_Ctrl_Att_RateCalCtrl1.csIresData_phi = Phi_ES;
    ipCS_Ctrl_Att_RateCalCtrl1.csIresData_theta = theta_ES;
    Memcpyx((unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csMnvData_A_Ref[0], (unint08 *)&Atti_Ref[0], sizeof(ipCS_Ctrl_Att_RateCalCtrl1.csMnvData_A_Ref));
    Memcpyx((unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csAttPara_Seq_AttD[0], (unint08 *)&Seq_AttD[0], sizeof(ipCS_Ctrl_Att_RateCalCtrl1.csAttPara_Seq_AttD));
    Memcpyx((unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_Rate_ESG[0], (unint08 *)&dAtti_ESG[0], sizeof(ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_Rate_ESG));
    Memcpyx((unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_wbo_ESG[0], (unint08 *)&wbo_ESG[0], sizeof(ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_wbo_ESG));
    Memcpyx((unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csOrbData_w0i[0], (unint08 *)&woi[0], sizeof(ipCS_Ctrl_Att_RateCalCtrl1.csOrbData_w0i));
    ipCS_Ctrl_Att_RateCalCtrl1.csCtrlerOtherPara_FP_BMC = FP_BMC;
    Memcpyx((unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_qri[0], (unint08 *)&qri[0], sizeof(ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_qri));
    Memcpyx((unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_wri[0], (unint08 *)&wri[0], sizeof(ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_wri));
    Memcpyx((unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csOrbData_coi[0][0], (unint08 *)&coi[0][0], sizeof(ipCS_Ctrl_Att_RateCalCtrl1.csOrbData_coi));
    Memcpyx((unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_w_ESG[0], (unint08 *)&w_ESG[0], sizeof(ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_w_ESG));
    Memcpyx((unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csCtrlerOtherPara_FP_Qctrl[0], (unint08 *)&FP_Qctrl[0], sizeof(ipCS_Ctrl_Att_RateCalCtrl1.csCtrlerOtherPara_FP_Qctrl));
    Memcpyx((unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csMnvData_dA_Ref[0], (unint08 *)&dAtti_Ref[0], sizeof(ipCS_Ctrl_Att_RateCalCtrl1.csMnvData_dA_Ref));
    Memcpyx((unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_A_STG[0], (unint08 *)&Atti_STG[0], sizeof(ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_A_STG));
    Memcpyx((unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_Rate_STG[0], (unint08 *)&dAtti_STG[0], sizeof(ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_Rate_STG));
    Memcpyx((unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_wbo_STG[0], (unint08 *)&wbo_STG[0], sizeof(ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_wbo_STG));
    Memcpyx((unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_Cbo_STG[0][0], (unint08 *)&Cbo_STG[0][0], sizeof(ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_Cbo_STG));
    Memcpyx((unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_A_STDyn[0], (unint08 *)&Atti_STDyn[0], sizeof(ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_A_STDyn));
    Memcpyx((unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_Rate_STDyn[0], (unint08 *)&dAtti_STDyn[0], sizeof(ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_Rate_STDyn));
    Memcpyx((unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_wbo_STDyn[0], (unint08 *)&wbo_STDyn[0], sizeof(ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_wbo_STDyn));
    Memcpyx((unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_Cbo_STDyn[0][0], (unint08 *)&Cbo_STG[0][0], sizeof(ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_Cbo_STDyn));
    ipCS_Ctrl_Att_RateCalCtrl1.csIresData_dPhi = dPhi_ES;
    ipCS_Ctrl_Att_RateCalCtrl1.csIresData_dTheta = dtheta_ES;
    Memcpyx((unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_A_Clp[0], (unint08 *)&Atti_Clp[0], sizeof(ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_A_Clp));
    Memcpyx((unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_Rate_Clp[0], (unint08 *)&dAtti_Clp[0], sizeof(ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_Rate_Clp));
    Memcpyx((unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_wbo_Clp[0], (unint08 *)&wbo_Clp[0], sizeof(ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_wbo_Clp));
    Memcpyx((unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_q_STG[0], (unint08 *)&q_STG[0], sizeof(ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_q_STG));
    Memcpyx((unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_A_c[0], (unint08 *)&Atti_C[0], sizeof(ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_A_c));
    Memcpyx((unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_w_STG[0], (unint08 *)&w_STG[0], sizeof(ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_w_STG));
    Memcpyx((unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_A_ESG[0], (unint08 *)&Atti_ESG[0], sizeof(ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_A_ESG));
    Memcpyx((unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_Cbo_ESG[0][0], (unint08 *)&Cbo_ESG[0][0], sizeof(ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_Cbo_ESG));
    Memcpyx((unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_qbt[0], (unint08 *)&qbt[0], sizeof(ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_qbt));
    IPCALL(ipCS_Ctrl_Att_RateCalCtrl1);
    // IP1: CS_Ctrl_Att_Rate - 输出变量赋值
    Memcpyx((unint08 *)&Rate_c[0], (unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_Rate_c[0], sizeof(Rate_c));
    Memcpyx((unint08 *)&w_Clp[0], (unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_w_Clp[0], sizeof(w_Clp));
    Memcpyx((unint08 *)&q_ESG[0], (unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_q_ESG[0], sizeof(q_ESG));
    Memcpyx((unint08 *)&Cbo_Clp[0][0], (unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_Cbo_Clp[0][0], sizeof(Cbo_Clp));
    Memcpyx((unint08 *)&Atti_Clp[0], (unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_A_Clp[0], sizeof(Atti_Clp));
    Memcpyx((unint08 *)&dAtti_Clp[0], (unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_Rate_Clp[0], sizeof(dAtti_Clp));
    Memcpyx((unint08 *)&wbo_Clp[0], (unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_wbo_Clp[0], sizeof(wbo_Clp));
    Memcpyx((unint08 *)&q_STG[0], (unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_q_STG[0], sizeof(q_STG));
    Memcpyx((unint08 *)&Atti_C[0], (unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_A_c[0], sizeof(Atti_C));
    Memcpyx((unint08 *)&w_STG[0], (unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_w_STG[0], sizeof(w_STG));
    Memcpyx((unint08 *)&Atti_ESG[0], (unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_A_ESG[0], sizeof(Atti_ESG));
    Memcpyx((unint08 *)&Cbo_ESG[0][0], (unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_Cbo_ESG[0][0], sizeof(Cbo_ESG));
    Memcpyx((unint08 *)&qbt[0], (unint08 *)&ipCS_Ctrl_Att_RateCalCtrl1.csAttCoreData_qbt[0], sizeof(qbt));

    // IP1: CS_AttCtrl_Propel - 输入参数赋值
    ipCS_AttCtrl_PropelCalCtrl2.csModeData_F_StopCtrl = F_StopCtrl;
    ipCS_AttCtrl_PropelCalCtrl2.m_WorkMode = WorkMode;
    Memcpyx((unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.ModeObjectTimer_Mode[0], (unint08 *)&Timer_Mode[0], sizeof(ipCS_AttCtrl_PropelCalCtrl2.ModeObjectTimer_Mode));
    ipCS_AttCtrl_PropelCalCtrl2.csWacqData_m_SubMode = m_SubMode;
    Memcpyx((unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csAttCoreData_A_c[0], (unint08 *)&Atti_C[0], sizeof(ipCS_AttCtrl_PropelCalCtrl2.csAttCoreData_A_c));
    Memcpyx((unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csAttCoreData_Rate_c[0], (unint08 *)&dAtti_C[0], sizeof(ipCS_AttCtrl_PropelCalCtrl2.csAttCoreData_Rate_c));
    ipCS_AttCtrl_PropelCalCtrl2.csJPCPara_FU = FU_thrGr;
    Memcpyx((unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csCtrlerOtherPara_FP_RWorCMGC[0], (unint08 *)&FP_RWorCMGC[0], sizeof(ipCS_AttCtrl_PropelCalCtrl2.csCtrlerOtherPara_FP_RWorCMGC));
    ipCS_AttCtrl_PropelCalCtrl2.csJPCData_F_UldT = F_UldT;
    ipCS_AttCtrl_PropelCalCtrl2.csSGAttAcqData_F_EarthAcq = F_EarthAcq;
    ipCS_AttCtrl_PropelCalCtrl2.csSGAttAcqData_F_YawCapt = F_YawCapt;
    ipCS_AttCtrl_PropelCalCtrl2.csIomScanPara_FP_GK_JetBack = FP_GK_JetBack;
    ipCS_AttCtrl_PropelCalCtrl2.csIomScanData_SMODE = SMODE;
    Memcpyx((unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csCtrlerDataJs_Use[0][0], (unint08 *)&Js_All[0][0], sizeof(ipCS_AttCtrl_PropelCalCtrl2.csCtrlerDataJs_Use));
    ipCS_AttCtrl_PropelCalCtrl2.csModeData_F_PanelUnfold = ID_Mass;
    Memcpyx((unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCData_mPhase_T[0], (unint08 *)&ThrGr[0], sizeof(ipCS_AttCtrl_PropelCalCtrl2.csJPCData_mPhase_T));
    Memcpyx((unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCData_mPhase_ThetaC_pst[0], (unint08 *)&mPhase_ThetaC_pst[0], sizeof(ipCS_AttCtrl_PropelCalCtrl2.csJPCData_mPhase_ThetaC_pst));
    Memcpyx((unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCData_mPhase_Region[0], (unint08 *)&mPhase_Region[0], sizeof(ipCS_AttCtrl_PropelCalCtrl2.csJPCData_mPhase_Region));
    Memcpyx((unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCData_mPhase_FJB[0], (unint08 *)&mPhase_FJB[0], sizeof(ipCS_AttCtrl_PropelCalCtrl2.csJPCData_mPhase_FJB));
    Memcpyx((unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCData_F_AssignUse[0], (unint08 *)&F_AssignUse[0], sizeof(ipCS_AttCtrl_PropelCalCtrl2.csJPCData_F_AssignUse));
    Memcpyx((unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCData_SumTn[0], (unint08 *)&SumTn[0], sizeof(ipCS_AttCtrl_PropelCalCtrl2.csJPCData_SumTn));
    Memcpyx((unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCData_SumTp[0], (unint08 *)&SumTp[0], sizeof(ipCS_AttCtrl_PropelCalCtrl2.csJPCData_SumTp));
    Memcpyx((unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCData_F_Jet[0], (unint08 *)&F_Jet[0], sizeof(ipCS_AttCtrl_PropelCalCtrl2.csJPCData_F_Jet));
    Memcpyx((unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCData_FJ[0], (unint08 *)&FJ[0], sizeof(ipCS_AttCtrl_PropelCalCtrl2.csJPCData_FJ));
    IPCALL(ipCS_AttCtrl_PropelCalCtrl2);
    // IP1: CS_AttCtrl_Propel - 输出变量赋值
    Memcpyx((unint08 *)&t[0], (unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCData_t_AC[0], sizeof(t));
    Memcpyx((unint08 *)&a[0], (unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCData_a[0], sizeof(a));
    Memcpyx((unint08 *)&a2[0], (unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCData_a2[0], sizeof(a2));
    Memcpyx((unint08 *)&SumTn2[0], (unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCData_SumTn2[0], sizeof(SumTn2));
    Memcpyx((unint08 *)&SumTp2[0], (unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCData_SumTp2[0], sizeof(SumTp2));
    Memcpyx((unint08 *)&t_AC[0], (unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCData_t_AC[0], sizeof(t_AC));
    Memcpyx((unint08 *)&F_st[0], (unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCData_F_st[0], sizeof(F_st));
    Memcpyx((unint08 *)&apn[0][0], (unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCData_apn[0][0], sizeof(apn));
    Memcpyx((unint08 *)&ThrGr[0], (unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCData_t[0], sizeof(ThrGr));
    Memcpyx((unint08 *)&mPhase_ThetaC_pst[0], (unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCData_mPhase_ThetaC_pst[0], sizeof(mPhase_ThetaC_pst));
    Memcpyx((unint08 *)&mPhase_Region[0], (unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCData_mPhase_Region[0], sizeof(mPhase_Region));
    Memcpyx((unint08 *)&F_Jet[0], (unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCData_F_Jet[0], sizeof(F_Jet));
    Memcpyx((unint08 *)&mPhase_FJB[0], (unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCData_mPhase_FJB[0], sizeof(mPhase_FJB));
    Memcpyx((unint08 *)&F_AssignUse[0], (unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCData_F_AssignUse[0], sizeof(F_AssignUse));
    Memcpyx((unint08 *)&SumTn[0], (unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCData_SumTn[0], sizeof(SumTn));
    Memcpyx((unint08 *)&SumTp[0], (unint08 *)&ipCS_AttCtrl_PropelCalCtrl2.csJPCData_SumTp[0], sizeof(SumTp));
  }
  // Set CycleNum CycleNum + 1;
  CycleNum = CycleNum + 1;
  // Set Timer_Mode[WorkMode_Lst] Timer_Mode[WorkMode_Lst] + Tc;
  Timer_Mode[WorkMode_Lst] = Timer_Mode[WorkMode_Lst] + Tc;
  if (WorkMode_Lst == 0x01u) {
    // ModeConvert_EIM 入轨消初偏模式切换
    Memcpyx((unint08 *)&ipModeConvert_EIMSwitchMode11.ModeObject_Timer_Mode[0], (unint08 *)&Timer_Mode[0], sizeof(ipModeConvert_EIMSwitchMode11.ModeObject_Timer_Mode));
    ipModeConvert_EIMSwitchMode11.m_WorkMode = WorkMode_Lst;

    IPCALL(ipModeConvert_EIMSwitchMode11);

    WorkMode = ipModeConvert_EIMSwitchMode11.m_WorkMode;
  }
  if (WorkMode_Lst == 0x00u) {
    // ModeConvert_SBM 主动段模式切换
    ipModeConvert_SBMSwitchMode12.m_starTime = StarTime;

    IPCALL(ipModeConvert_SBMSwitchMode12);

    WorkMode = ipModeConvert_SBMSwitchMode12.m_WorkMode;
  }
  if (WorkMode_Lst != WorkMode) {
    // Set WorkMode_Lst  WorkMode;
    WorkMode_Lst = WorkMode;
    // Set Timer_Mode[WorkMode_Lst]  0.0 ;
    Timer_Mode[WorkMode_Lst] = 0.0;
    // Set Atti_Trgt  {0.0,0.0,0.0} ;
    Atti_Trgt[0] = 0.0;
    Atti_Trgt[1] = 0.0;
    Atti_Trgt[2] = 0.0;
  }
  if (F_DTOrbitEUpdate == 1) {
    // Set t_next StarTime + Tc ;
    t_next = StarTime + Tc;
  }
  if (WorkMode_Lst != 0x00u) {
    // IP1: CS_PrecessionNutationCal - 输入参数赋值
    ipCS_PrecessionNutationCalCalEnv1.tmpT = 0;
    ipCS_PrecessionNutationCalCalEnv1.csOrbOtherPara_FS_CPNCal = FS_CPNCal;
    Memcpyx((unint08 *)&ipCS_PrecessionNutationCalCalEnv1.csOrb19_qd[0], (unint08 *)&qJD[0], sizeof(ipCS_PrecessionNutationCalCalEnv1.csOrb19_qd));
    IPCALL(ipCS_PrecessionNutationCalCalEnv1);
    // IP1: CS_PrecessionNutationCal - 输出变量赋值
    F_qJDerr = ipCS_PrecessionNutationCalCalEnv1.csOrbDataOther_F_qJDerr;
    Memcpyx((unint08 *)&CPN[0][0], (unint08 *)&ipCS_PrecessionNutationCalCalEnv1.CPN[0][0], sizeof(CPN));
    Memcpyx((unint08 *)&qJD[0], (unint08 *)&ipCS_PrecessionNutationCalCalEnv1.csOrb19_qd[0], sizeof(qJD));

    // IP1: CS_OrbitComputation - 输入参数赋值
    ipCS_OrbitComputationCalEnv2.m_starTime_Next = t_next;
    Memcpyx((unint08 *)&ipCS_OrbitComputationCalEnv2.csOrbOtherPara_FP_OrbUpdate[0], (unint08 *)&FP_OrbUpdate[0], sizeof(ipCS_OrbitComputationCalEnv2.csOrbOtherPara_FP_OrbUpdate));
    ipCS_OrbitComputationCalEnv2.csOrbOtherPara_FP_UseOtherOrb = FP_UseOtherOrb;
    ipCS_OrbitComputationCalEnv2.csOrbOtherPara_FP_WoPrecession = FP_WoPrecession;
    ipCS_OrbitComputationCalEnv2.csOrbDataOther_F_DTOrbitEUpdate = F_DTOrbitEUpdate;
    ipCS_OrbitComputationCalEnv2.m_WorkMode = WorkMode;
    ipCS_OrbitComputationCalEnv2.pOrbI_t0 = 0;
    ipCS_OrbitComputationCalEnv2.pOrbI_deltaa0 = 0;
    ipCS_OrbitComputationCalEnv2.pOrbI_adelta = 0;
    ipCS_OrbitComputationCalEnv2.pOrbI_i0 = 0;
    ipCS_OrbitComputationCalEnv2.pOrbI_omg0 = 0;
    ipCS_OrbitComputationCalEnv2.pOrbI_omg1 = 0;
    ipCS_OrbitComputationCalEnv2.pOrbI_kesid = 0;
    ipCS_OrbitComputationCalEnv2.pOrbI_etad = calc_cosrou_norm;
    ipCS_OrbitComputationCalEnv2.pOrbI_w1 = 0;
    ipCS_OrbitComputationCalEnv2.pOrbI_etam = 0;
    ipCS_OrbitComputationCalEnv2.pOrbI_a = 0;
    ipCS_OrbitComputationCalEnv2.pOrbI_beta = 0;
    ipCS_OrbitComputationCalEnv2.pOrbI_lmd0 = 0;
    ipCS_OrbitComputationCalEnv2.pOrbI_lmd1 = calc_cosrou_norm;
    ipCS_OrbitComputationCalEnv2.pOrbI_lmd2 = 0;
    ipCS_OrbitComputationCalEnv2.pOrbI_lmdg = 0;
    ipCS_OrbitComputationCalEnv2.pOrbG_t0 = 0;
    ipCS_OrbitComputationCalEnv2.pOrbG_deltaa0 = 0;
    ipCS_OrbitComputationCalEnv2.pOrbG_adelta = 0;
    ipCS_OrbitComputationCalEnv2.pOrbG_i0 = 0;
    ipCS_OrbitComputationCalEnv2.pOrbG_omg0 = 0;
    ipCS_OrbitComputationCalEnv2.pOrbG_omg1 = 0;
    ipCS_OrbitComputationCalEnv2.pOrbG_kesid = 0;
    ipCS_OrbitComputationCalEnv2.pOrbG_etad = calc_cosrou_norm;
    ipCS_OrbitComputationCalEnv2.pOrbG_w1 = 0;
    ipCS_OrbitComputationCalEnv2.pOrbG_etam = 0;
    ipCS_OrbitComputationCalEnv2.pOrbG_a = 0;
    ipCS_OrbitComputationCalEnv2.pOrbG_beta = 0;
    ipCS_OrbitComputationCalEnv2.pOrbG_lmd0 = 0;
    ipCS_OrbitComputationCalEnv2.pOrbG_lmd1 = 0;
    ipCS_OrbitComputationCalEnv2.pOrbG_lmd2 = 0;
    ipCS_OrbitComputationCalEnv2.pOrbG_lmdg = 0;
    ipCS_OrbitComputationCalEnv2.pGpsPara_FS_UseType = FS_UseType;
    IPCALL(ipCS_OrbitComputationCalEnv2);
    // IP1: CS_OrbitComputation - 输出变量赋值
    F_TurnAAM = ipCS_OrbitComputationCalEnv2.csOrbitErrJData_F_TurnAAM;
    FV = ipCS_OrbitComputationCalEnv2.pObtOut_FV;
    Memcpyx((unint08 *)&F_SunlightZone[0], (unint08 *)&ipCS_OrbitComputationCalEnv2.pObtOut_F_SunlightZone[0], sizeof(F_SunlightZone));
    FV_NoInsert = ipCS_OrbitComputationCalEnv2.pObtOut_FV_NoInsert;
    Memcpyx((unint08 *)&OrbOut, (unint08 *)&ipCS_OrbitComputationCalEnv2.pObtOut_FV, sizeof(OrbOut));
  }
  if (WorkMode_Lst == 0x01u) {
    // IP1: CS_TrgtAtt_EIM - 输入参数赋值
    ipCS_TrgtAtt_EIMCalTar1.m_WorkMode = WorkMode;
    Memcpyx((unint08 *)&ipCS_TrgtAtt_EIMCalTar1.csMnvData_A_Trgt[0], (unint08 *)&Atti_Trgt[0], sizeof(ipCS_TrgtAtt_EIMCalTar1.csMnvData_A_Trgt));
    Memcpyx((unint08 *)&ipCS_TrgtAtt_EIMCalTar1.csAttPara_Seq_AttD[0], (unint08 *)&Seq_AttD[0], sizeof(ipCS_TrgtAtt_EIMCalTar1.csAttPara_Seq_AttD));
    Memcpyx((unint08 *)&ipCS_TrgtAtt_EIMCalTar1.csOrbData_coi[0][0], (unint08 *)&OrbOut.coi[0][0], sizeof(ipCS_TrgtAtt_EIMCalTar1.csOrbData_coi));
    Memcpyx((unint08 *)&ipCS_TrgtAtt_EIMCalTar1.csOrbData_w0i[0], (unint08 *)&woi[0], sizeof(ipCS_TrgtAtt_EIMCalTar1.csOrbData_w0i));
    IPCALL(ipCS_TrgtAtt_EIMCalTar1);
    // IP1: CS_TrgtAtt_EIM - 输出变量赋值
    Memcpyx((unint08 *)&Cro[0][0], (unint08 *)&ipCS_TrgtAtt_EIMCalTar1.csAttCoreData_Cro[0][0], sizeof(Cro));
    Memcpyx((unint08 *)&wri[0], (unint08 *)&ipCS_TrgtAtt_EIMCalTar1.csAttCoreData_wri[0], sizeof(wri));
    Memcpyx((unint08 *)&wro[0], (unint08 *)&ipCS_TrgtAtt_EIMCalTar1.csAttCoreData_wro[0], sizeof(wro));
    Memcpyx((unint08 *)&qri[0], (unint08 *)&ipCS_TrgtAtt_EIMCalTar1.csAttCoreData_qri[0], sizeof(qri));

    // IP1: CS_Track_Atti - 输入参数赋值
    Memcpyx((unint08 *)&ipCS_Track_AttiCalTar2.csAttCoreData_Cro[0][0], (unint08 *)&Cro[0][0], sizeof(ipCS_Track_AttiCalTar2.csAttCoreData_Cro));
    Memcpyx((unint08 *)&ipCS_Track_AttiCalTar2.csAttPara_Seq_AttD[0], (unint08 *)&Seq_AttD[0], sizeof(ipCS_Track_AttiCalTar2.csAttPara_Seq_AttD));
    ipCS_Track_AttiCalTar2.m_WorkMode = WorkMode;
    Memcpyx((unint08 *)&ipCS_Track_AttiCalTar2.csAttCoreData_wro[0], (unint08 *)&wro[0], sizeof(ipCS_Track_AttiCalTar2.csAttCoreData_wro));
    Memcpyx((unint08 *)&ipCS_Track_AttiCalTar2.csAttCoreData_wri[0], (unint08 *)&wri[0], sizeof(ipCS_Track_AttiCalTar2.csAttCoreData_wri));
    IPCALL(ipCS_Track_AttiCalTar2);
    // IP1: CS_Track_Atti - 输出变量赋值
    Memcpyx((unint08 *)&Atti_Ref[0], (unint08 *)&ipCS_Track_AttiCalTar2.csMnvData_A_Ref[0], sizeof(Atti_Ref));
    Memcpyx((unint08 *)&dAtti_Ref[0], (unint08 *)&ipCS_Track_AttiCalTar2.csMnvData_dA_Ref[0], sizeof(dAtti_Ref));
    Memcpyx((unint08 *)&ddAtti_Ref[0], (unint08 *)&ipCS_Track_AttiCalTar2.csMnvData_ddA_Ref[0], sizeof(ddAtti_Ref));
    Memcpyx((unint08 *)&TorqRef[0], (unint08 *)&ipCS_Track_AttiCalTar2.csMnvData_TorqRef[0], sizeof(TorqRef));
  }
  if (WorkMode_Lst == 0x02u) {
    // IP1: CS_TrgtAtt_NWM_USU - 输入参数赋值
    ipCS_TrgtAtt_NWM_USUCalTar3.csDriftAngData_Psi_DA = psi_DA;
    Memcpyx((unint08 *)&ipCS_TrgtAtt_NWM_USUCalTar3.csAttPara_Seq_AttD[0], (unint08 *)&Seq_AttD[0], sizeof(ipCS_TrgtAtt_NWM_USUCalTar3.csAttPara_Seq_AttD));
    ipCS_TrgtAtt_NWM_USUCalTar3.m_WorkMode = WorkMode;
    Memcpyx((unint08 *)&ipCS_TrgtAtt_NWM_USUCalTar3.csOrbData_w0i[0], (unint08 *)&woi[0], sizeof(ipCS_TrgtAtt_NWM_USUCalTar3.csOrbData_w0i));
    ipCS_TrgtAtt_NWM_USUCalTar3.csDriftAngData_dPsi_DA = dpsi_DA;
    Memcpyx((unint08 *)&ipCS_TrgtAtt_NWM_USUCalTar3.csOrbData_coi[0][0], (unint08 *)&OrbOut.coi[0][0], sizeof(ipCS_TrgtAtt_NWM_USUCalTar3.csOrbData_coi));
    IPCALL(ipCS_TrgtAtt_NWM_USUCalTar3);
    // IP1: CS_TrgtAtt_NWM_USU - 输出变量赋值
    Memcpyx((unint08 *)&wro[0], (unint08 *)&ipCS_TrgtAtt_NWM_USUCalTar3.csAttCoreData_wro[0], sizeof(wro));
    Memcpyx((unint08 *)&A_Ref_si[0], (unint08 *)&ipCS_TrgtAtt_NWM_USUCalTar3.csMnvData_A_Ref_si[0], sizeof(A_Ref_si));
    Memcpyx((unint08 *)&Cro[0][0], (unint08 *)&ipCS_TrgtAtt_NWM_USUCalTar3.csAttCoreData_Cro[0][0], sizeof(Cro));
    Memcpyx((unint08 *)&Cro_si[0][0], (unint08 *)&ipCS_TrgtAtt_NWM_USUCalTar3.csAttCoreData_Cro_si[0][0], sizeof(Cro_si));
    Memcpyx((unint08 *)&wri[0], (unint08 *)&ipCS_TrgtAtt_NWM_USUCalTar3.csAttCoreData_wri[0], sizeof(wri));
    Memcpyx((unint08 *)&wri_si[0], (unint08 *)&ipCS_TrgtAtt_NWM_USUCalTar3.csAttCoreData_wri_si[0], sizeof(wri_si));
    Memcpyx((unint08 *)&qri[0], (unint08 *)&ipCS_TrgtAtt_NWM_USUCalTar3.csAttCoreData_qri[0], sizeof(qri));

    // IP1: CS_Track_Atti - 输入参数赋值
    Memcpyx((unint08 *)&ipCS_Track_AttiCalTar4.csAttCoreData_Cro[0][0], (unint08 *)&Cro[0][0], sizeof(ipCS_Track_AttiCalTar4.csAttCoreData_Cro));
    Memcpyx((unint08 *)&ipCS_Track_AttiCalTar4.csAttPara_Seq_AttD[0], (unint08 *)&Seq_AttD[0], sizeof(ipCS_Track_AttiCalTar4.csAttPara_Seq_AttD));
    ipCS_Track_AttiCalTar4.m_WorkMode = WorkMode;
    Memcpyx((unint08 *)&ipCS_Track_AttiCalTar4.csAttCoreData_wro[0], (unint08 *)&wro[0], sizeof(ipCS_Track_AttiCalTar4.csAttCoreData_wro));
    Memcpyx((unint08 *)&ipCS_Track_AttiCalTar4.csAttCoreData_wri[0], (unint08 *)&wri[0], sizeof(ipCS_Track_AttiCalTar4.csAttCoreData_wri));
    IPCALL(ipCS_Track_AttiCalTar4);
    // IP1: CS_Track_Atti - 输出变量赋值
    Memcpyx((unint08 *)&Atti_Ref[0], (unint08 *)&ipCS_Track_AttiCalTar4.csMnvData_A_Ref[0], sizeof(Atti_Ref));
    Memcpyx((unint08 *)&dAtti_Ref[0], (unint08 *)&ipCS_Track_AttiCalTar4.csMnvData_dA_Ref[0], sizeof(dAtti_Ref));
    Memcpyx((unint08 *)&ddAtti_Ref[0], (unint08 *)&ipCS_Track_AttiCalTar4.csMnvData_ddA_Ref[0], sizeof(ddAtti_Ref));
    Memcpyx((unint08 *)&TorqRef[0], (unint08 *)&ipCS_Track_AttiCalTar4.csMnvData_TorqRef[0], sizeof(TorqRef));
  }
  return;
}
#ifndef __GCC_COMPILED__
int main() {
  NWMInit();
  while (1) {
    NWMTask();
  }
  return 0;
}
#endif