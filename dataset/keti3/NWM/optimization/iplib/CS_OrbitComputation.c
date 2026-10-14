#include "NWM.h"
#include "CS_OrbitComputation.h"

void SunEphemerisCalculate(void *p);
void OrbitCalculate(void *p);

void CS_OrbitComputationFun(void *p)
{
    CS_OrbitComputation *pIp = (CS_OrbitComputation*)p;
    float64 tmpF;
        unint32 i;

        /* (1) 轨道根数选取 */
        if ((FP_OrbUpdate[WorkMode] == 1) &&
            (F_DTOrbitEUpdate == 1))
        { /* 允许更新轨道根数 或 姿态机动等模式使用GPS数据 */
            if ( (FS_UseType == 1) || (FS_UseType == 2) )       /* 引入GPS数据校验（轨道板或通道板） */
            {
                // pIp->pOrbPara.t0 = pIp->pOrbG.t0;
                // pIp->pOrbPara.deltaa0 = pIp->pOrbG.deltaa0;
                // pIp->pOrbPara.adelta = pIp->pOrbG.adelta;
                // pIp->pOrbPara.i0 = pIp->pOrbG.i0;
                // pIp->pOrbPara.omg0 = pIp->pOrbG.omg0;
                // pIp->pOrbPara.omg1 = pIp->pOrbG.omg1;
                // pIp->pOrbPara.kesid = pIp->pOrbG.kesid;
                // pIp->pOrbPara.etad = pIp->pOrbG.etad;
                // pIp->pOrbPara.w1 = pIp->pOrbG.w1;
                // pIp->pOrbPara.etam = pIp->pOrbG.etam;
                // pIp->pOrbPara.a = pIp->pOrbG.a;
                // pIp->pOrbPara.beta = pIp->pOrbG.beta;
                // pIp->pOrbPara.lmd0 = pIp->pOrbG.lmd0;
                // pIp->pOrbPara.lmd1 = pIp->pOrbG.lmd1;
                // pIp->pOrbPara.lmd2 = pIp->pOrbG.lmd2;
                // pIp->pOrbPara.lmdg = pIp->pOrbG.lmdg;
                Memcpyx((unint08 *)&pIp->pOrbPara.t0, (unint08 *)&pIp->pOrbG.t0, sizeof(SOrbitParameterX));
            }
            else
            {
                // pIp->pOrbPara.t0 = pIp->pOrbI.t0;
                // pIp->pOrbPara.deltaa0 = pIp->pOrbI.deltaa0;
                // pIp->pOrbPara.adelta = pIp->pOrbI.adelta;
                // pIp->pOrbPara.i0 = pIp->pOrbI.i0;
                // pIp->pOrbPara.omg0 = pIp->pOrbI.omg0;
                // pIp->pOrbPara.omg1 = pIp->pOrbI.omg1;
                // pIp->pOrbPara.kesid = pIp->pOrbI.kesid;
                // pIp->pOrbPara.etad = pIp->pOrbI.etad;
                // pIp->pOrbPara.w1 = pIp->pOrbI.w1;
                // pIp->pOrbPara.etam = pIp->pOrbI.etam;
                // pIp->pOrbPara.a = pIp->pOrbI.a;
                // pIp->pOrbPara.beta = pIp->pOrbI.beta;
                // pIp->pOrbPara.lmd0 = pIp->pOrbI.lmd0;
                // pIp->pOrbPara.lmd1 = pIp->pOrbI.lmd1;
                // pIp->pOrbPara.lmd2 = pIp->pOrbI.lmd2;
                // pIp->pOrbPara.lmdg = pIp->pOrbI.lmdg;
                Memcpyx((unint08 *)&pIp->pOrbPara, (unint08 *)&pIp->pOrbI, sizeof(SOrbitParameterX));
            }

            if (FP_UseOtherOrb == 1)
            {
                /* Orb采用其他轨道参数，如自主导航结果（待扩展） */
                f_Fun_Null();
            }
        }

        pIp->pObtOut_FV = 1;    /* 轨道数据有效 */

        /* (2) 调用《近圆中低轨卫星轨道根数外推算法》计算卫星轨道 */
        OrbitCalculate(pIp);
        SunEphemerisCalculate(pIp);

        /* (3) 计算qoi */
        C2Q(pIp->pOrbData.qoi, pIp->pOrbData.coi[0]);

        /* (4) 轨道有效性判断 */
        if (Fabsx(t_next - pIp->pOrbPara.t0) >= Lmt_dT)
        {
            pIp->pObtOut_FV = 0;    /* 轨道数据无效 */
        }

        FV_NoInsert = 0;    /* 轨道数据注入 */
        if (Fabsx(t_next - pIp->pOrbPara.t0) >= (Lmt_dT * 0.7))
        {
            FV_NoInsert = 1;    /* 轨道数据未注入 */
        }

        if (pIp->pOrbData.F_OrbAbnorm == 0)     /* 规范化算法计算异常w0 */
        {
            pIp->pObtOut_FV = 0;    /* 轨道数据无效 */
        }

        if ((WorkMode != 0x09u) && (WorkMode != 0x08u) && (pIp->pObtOut_FV == 0))     /* 轨道计算异常 */
        {
            pIp->csOrbitErrJData_Cnt_NoOrb ++;
        }
        else
        {
            pIp->csOrbitErrJData_Cnt_NoOrb = 0;
        }

        if (pIp->csOrbitErrJData_Cnt_NoOrb >= Num_NoOrb)
        {
            if (FS_NoOrbPro == 0x0)
            {
                for (i=0; i<3; i++)
                {
                    F_SunlightZone[i] = 1;         /* 阳照区 */
                }
                pIp->pOrbData.so[2] = -0.5;         /* 给定So值，模为1 */
                pIp->pOrbData.so[1] =  0.5;
                pIp->pOrbData.so[0] =  0.707106781186548;
                pIp->pOrbData.w0     = calc_w0_norm;
                pIp->pOrbData.cosrou = calc_cosrou_norm;
            }
            else
            {
                F_TurnAAM = 0x1;
            }
        }

        /* (5) 计算 考虑轨道进动的轨道系相对于惯性J2000.0的角速度 */
        if (FP_WoPrecession == 0)        /* 不考虑轨道进动 */
        {
            pIp->pOrbData.w0i[0] = 0.0;
            pIp->pOrbData.w0i[1] = -pIp->pOrbData.w0;
            pIp->pOrbData.w0i[2] = 0.0;
        }
        else
        {
            pIp->pOrbData.w0i[0] = 0.0;
            pIp->pOrbData.w0i[1] = -pIp->pOrbData.w0;
            pIp->pOrbData.w0i[2] = -2.0 * pIp->pOrbPara.omg1 * Sinx(pIp->pOrbData.u) * Sinx(pIp->pOrbData.i);
        }

        /* (6)OrbOut.Cz_λG=Rz(Orb.λG + Earth.ω*(t_next - Orb.t0)); */
        tmpF = pIp->pOrbPara.lmdg + We * (t_next - pIp->pOrbPara.t0);
        Rz(&pIp->pOrbData.Cz_lmdG[0][0], tmpF);

        pIp->pOrbData.lmdG = pIp->pOrbPara.lmdg + We * (t_next - pIp->pOrbPara.t0);


        return;
}


void SunEphemerisCalculate(void *p)
{
    CS_OrbitComputation *pIp = (CS_OrbitComputation*)p;
    float64 deltat;

    float64 msun;
    float64 comgsun;
    float64 somgsun;
    float64 susun;
    float64 cusun;
    float64 sisun;
    float64 cisun;

    deltat = t_next - pIp->pOrbPara.t0;

    /* g. 太阳轨道及方位计算 */
    msun = dMSun * deltat + pIp->pOrbPara.msun0;
    msun = ModPNHP(msun, PI);
    pIp->pOrbData.us = msun + 2.0 * eSun * Sinx(msun) + pIp->pOrbPara.wsun + 1.25 * eSun * eSun * Sinx(2.0 * msun);
    pIp->pOrbData.us = ModPNHP(pIp->pOrbData.us, PI);

    somgsun = Sinx(pIp->pOrbPara.omgsun);
    comgsun = Cosx(pIp->pOrbPara.omgsun);
    susun = Sinx(pIp->pOrbData.us);
    cusun = Cosx(pIp->pOrbData.us);
    sisun = Sinx(iSun);
    cisun = Cosx(iSun);
    /* SI计算 */
    pIp->pOrbData.si[0] = comgsun * cusun - somgsun * cisun * susun;
    pIp->pOrbData.si[1] = somgsun * cusun + comgsun * cisun * susun;
    pIp->pOrbData.si[2] = sisun * susun;

    /* SO计算 */
    MatrixMulti(pIp->pOrbData.so, pIp->pOrbData.coi[0], pIp->pOrbData.si,  3, 3, 1);

    return;
}

void OrbitCalculate(void *point)
{
    CS_OrbitComputation *pIp = (CS_OrbitComputation*)point;
    unint32  counter;
    float64  deltat;
    float64  pp;
    float64  a2p;
    float64  si0;
    float64  ci0;
    float64  ssi;
    float64  s2n;
    float64  c2n;
    float64  as;
    float64  is;
    float64  omgs;
    float64  kesis;
    float64  etas;
    float64  lmds;
    float64  up;
    /* float64 prevup; */
    float64  ar;
    float64  te;
    float64  tef;
    float64  si;
    float64  ci;
    float64  su;
    float64  cu;
    float64  somg;
    float64  comg;
    float64  p;
    float64  dr;
    float64  h;
    float64  hh[3];
    float64  rdr;
    float64  rr;
    float64  tus;
    float64  tmpas1;
    float64  tmpas2;

    float64  us;
    float64  tmpas3;
    float64  tmpas4;
    float64  sUS;
    float64  cUS;

    counter = 0;
    deltat = t_next - pIp->pOrbPara.t0;

    /* a. 平根数计算 */
    pIp->pOrbData.ap = Re + pIp->pOrbPara.deltaa0 + pIp->pOrbPara.adelta * deltat; /* ~a */
    pIp->pOrbData.omgp = pIp->pOrbPara.omg0 + pIp->pOrbPara.omg1 * deltat; /* ~omg */
    pIp->pOrbData.omgp = ModPNHP(pIp->pOrbData.omgp, PI);
    pIp->pOrbData.kesip = pIp->pOrbPara.a * Cosx(pIp->pOrbPara.w1 * deltat - pIp->pOrbPara.beta) +  pIp->pOrbPara.kesid * deltat; /* ~ksi */
    pIp->pOrbData.etap = -pIp->pOrbPara.a * Sinx(pIp->pOrbPara.w1 * deltat - pIp->pOrbPara.beta) +  pIp->pOrbPara.etad * deltat + pIp->pOrbPara.etam; /* ~eta */
    pIp->pOrbData.lmdp = pIp->pOrbPara.lmd0 + pIp->pOrbPara.lmd1 * deltat + pIp->pOrbPara.lmd2 * deltat * deltat;/* ~lmd */
    pIp->pOrbData.lmdp = ModPNHP(pIp->pOrbData.lmdp, PI);
    pp = pIp->pOrbData.ap * (1.0 - pIp->pOrbData.kesip * pIp->pOrbData.kesip - pIp->pOrbData.etap * pIp->pOrbData.etap); /* ~p */
    pIp->pOrbData.ip = pIp->pOrbPara.i0;

    /* b. 短周期项计算 */
    /* 椭圆轨道,兼容圆轨道 */
    a2p = A2 / (pp * pp);
    si0 = Sinx(pIp->pOrbPara.i0);
    ci0 = Cosx(pIp->pOrbPara.i0);
    ssi = si0 * si0;

    up = pIp->pOrbData.lmdp;
    do
    {
        counter++;  /* 连续计数 */

        /* prevup = up; */
        up = pIp->pOrbData.lmdp + pIp->pOrbData.kesip * Sinx(up) + pIp->pOrbData.etap * Cosx(up);
    } while(counter < 6);

    /* 椭圆轨道短周期项计算 */
    ar = 1.0 / (1.0 - pIp->pOrbData.kesip * Cosx(up) + pIp->pOrbData.etap * Sinx(up));

    //tus = ar * (up-lmdp) * (1.0 + 0.5 * etap * Sinx(up) - 0.5 * kesip * Cosx(up));
    tus = ar * (up-pIp->pOrbData.lmdp) * (1.0 + 1.0 / (1.0 + Sqrtx(1.0 - (pIp->pOrbData.kesip * pIp->pOrbData.kesip + pIp->pOrbData.etap * pIp->pOrbData.etap)))
                                *(pIp->pOrbData.etap * Sinx(up) - pIp->pOrbData.kesip * Cosx(up)) );
    tus = LimitDouble(tus,1.0);
    us = up + Asinx(tus);

    s2n = Sinx(2.0 * us);
    c2n = Cosx(2.0 * us);

    /* a~
    as    = ocp->A2 * (2.0/3.0 * (1.0 - 1.5*ssi) * (ar * ar * ar - 1.0 - 1.5*(kesip * kesip + etap * etap))
                        + ssi * ar * ar * ar * c2n) / ap;
    To avoid SOC2008 CPU abnomal trap8 reset, break fmuld-fmuld-fdivd-fmuld-std-call order,Modify above code sequence fxt  */

    tmpas1 = A2 / pIp->pOrbData.ap;
    tmpas2 = 2.0/3.0 * (1.0 - 1.5*ssi);
    tmpas3 = ar * ar * ar - 1.0 - 1.5*(pIp->pOrbData.kesip * pIp->pOrbData.kesip + pIp->pOrbData.etap * pIp->pOrbData.etap);
    tmpas4 = ssi * ar * ar * ar * c2n;

    as = tmpas1 * (tmpas2 * tmpas3 + tmpas4);

    sUS = Sinx(us);
    cUS = Cosx(us);

    /* i~ */
    is    = a2p * si0 * ci0 * (pIp->pOrbData.kesip * cUS + pIp->pOrbData.etap * sUS + c2n
                                + 1.0 / 3.0 * (pIp->pOrbData.kesip * Cosx(3.0 * us) - pIp->pOrbData.etap * Sinx(3.0 * us))) / 2.0;
    /* omg~ */
    omgs  = a2p * ci0 * (-(us - pIp->pOrbData.lmdp) - (0.5 * pIp->pOrbData.kesip * sUS + 1.5 * pIp->pOrbData.etap * cUS)
                            + 0.5 * s2n + 1.0/6.0 * (pIp->pOrbData.kesip * Sinx(3.0*us) + pIp->pOrbData.etap * Cosx(3.0*us))  )  ;
    /* kesi~ */
    kesis = a2p * (cUS + 0.5 * pIp->pOrbData.kesip * c2n - pIp->pOrbData.etap * s2n + pIp->pOrbData.kesip
                    + ssi * (-1.25 * cUS + 0.5 * pIp->pOrbData.kesip * c2n + 2.0 * pIp->pOrbData.etap * s2n
                            + 7.0 / 12.0 * Cosx(3.0*us) + 0.375 * (pIp->pOrbData.kesip * Cosx(4.0*us) - pIp->pOrbData.etap * Sinx(4.0*us)) - 1.25*pIp->pOrbData.kesip));
    /* eta~ */
    etas  = a2p * (-sUS - 0.5 * pIp->pOrbData.etap * c2n + pIp->pOrbData.etap
                    + ssi *(1.75 * sUS - 0.5 * pIp->pOrbData.kesip * s2n + 2.0 * pIp->pOrbData.etap * c2n
                            - 7.0 / 12.0 * Sinx(3.0*us) - 0.375 * (pIp->pOrbData.kesip * Sinx(4.0*us) + pIp->pOrbData.etap * Cosx(4.0*us)) - 1.25*pIp->pOrbData.etap));
    /* lmd~ */
    lmds  = -ci0 * omgs + a2p * ((1.0 - 1.5*ssi)*(us - pIp->pOrbData.lmdp) + 1.5 * (pIp->pOrbData.kesip * sUS + pIp->pOrbData.etap * cUS)
                                    + ssi * (-1.625 * pIp->pOrbData.kesip * sUS - 2.875 * pIp->pOrbData.etap * cUS + 0.75*s2n
                                    + 13.0/24.0 * (pIp->pOrbData.kesip * Sinx(3.0*us) + pIp->pOrbData.etap * Cosx(3.0 * us) )));

    /* c. 瞬时轨道根数计算 */
    pIp->pOrbData.a = pIp->pOrbData.ap+ as;  /* 卫星a计算 */
    pIp->pOrbData.i = pIp->pOrbPara.i0 + is; /* 卫星i计算 */
    pIp->pOrbData.omg = pIp->pOrbData.omgp + omgs; /* 卫星omg计算 */
    pIp->pOrbData.omg = ModPNHP(pIp->pOrbData.omg, PI);

    pIp->pOrbData.kesi = pIp->pOrbData.kesip + kesis; /* 卫星ksi计算 */
    pIp->pOrbData.eta = pIp->pOrbData.etap + etas;

    pIp->pOrbData.lmd = pIp->pOrbData.lmdp + lmds;  /* 卫星lmd计算 */
    pIp->pOrbData.lmd = ModPNHP(pIp->pOrbData.lmd, PI);

    /* 卫星e计算 */
    pIp->pOrbData.e = Sqrtx(pIp->pOrbData.kesi * pIp->pOrbData.kesi + pIp->pOrbData.eta * pIp->pOrbData.eta);

    up = pIp->pOrbData.lmd;
    counter = 0;

    do
    {
        counter++;  /* 连续计数 */

        /* prevup = up; */
        up = pIp->pOrbData.lmd + pIp->pOrbData.kesi * Sinx(up) + pIp->pOrbData.eta * Cosx(up);
    } while(counter < 6);

    ar = 1.0 / (1.0 - pIp->pOrbData.kesi * Cosx(up) + pIp->pOrbData.eta * Sinx(up));

    te = Sqrtx(1.0 - pIp->pOrbData.e * pIp->pOrbData.e);
    /* 卫星u计算 */
    tus = ar * (up - pIp->pOrbData.lmd) *
        (1.0 + (pIp->pOrbData.eta * Sinx(up) - pIp->pOrbData.kesi * Cosx(up)) / (1.0 + te));
    tus = LimitDouble(tus,1.0);
    pIp->pOrbData.u = up + Asinx(tus);
    pIp->pOrbData.u = ModPNHP(pIp->pOrbData.u, PI);

    /* 卫星r计算 */
    pIp->pOrbData.r = pIp->pOrbData.a / ar;

    /* 卫星w计算 */
    pIp->pOrbData.w = Atan2x(-pIp->pOrbData.eta, pIp->pOrbData.kesi);

    /* 卫星f计算 */
    pIp->pOrbData.f  = pIp->pOrbData.u - pIp->pOrbData.w;
    pIp->pOrbData.f  = ModPNHP(pIp->pOrbData.f , PI);

    tef = Sqrtx(Mu * pIp->pOrbData.a) * te;

    /* 卫星w0计算 */
    pIp->pOrbData.w0 = tef / (pIp->pOrbData.r * pIp->pOrbData.r);

    /* w0误差判断 */
    if (Fabsx(pIp->pOrbData.w0 - calc_w0_norm) > calc_Lmt_dw0)
    {
        pIp->pOrbData.w0 = calc_w0_norm;
        pIp->pOrbData.r = calc_r_norm;
        pIp->pOrbData.F_OrbAbnorm = 0;
    }
    else
    {
        pIp->pOrbData.F_OrbAbnorm = 1;
    }

    /* d. 轨道坐标系相对于J2000.0历元惯性坐标系或瞬时平赤道地心坐标系方向余弦阵 */
    si   = Sinx(pIp->pOrbData.i);
    ci   = Cosx(pIp->pOrbData.i);
    su   = Sinx(pIp->pOrbData.u);
    cu   = Cosx(pIp->pOrbData.u);
    somg = Sinx(pIp->pOrbData.omg);
    comg = Cosx(pIp->pOrbData.omg);

    /* coi计算 */
    pIp->pOrbData.coi[0][0] = -su * comg - cu * ci * somg;
    pIp->pOrbData.coi[0][1] = -su * somg + cu * ci * comg;
    pIp->pOrbData.coi[0][2] =  cu * si;

    pIp->pOrbData.coi[1][0] = -si * somg;
    pIp->pOrbData.coi[1][1] =  si * comg;
    pIp->pOrbData.coi[1][2] = -ci;

    pIp->pOrbData.coi[2][0] = -cu * comg + su * ci * somg;
    pIp->pOrbData.coi[2][1] = -cu * somg - su * ci * comg;
    pIp->pOrbData.coi[2][2] = -su * si;

    /* e. 地心经度L、纬度δ和地球半张角余弦计算 */
    pIp->pOrbData.l1 = Atan2x(su * ci, cu);
    pIp->pOrbData.l = pIp->pOrbData.l1 + pIp->pOrbData.omg - pIp->pOrbPara.lmdg - We * deltat;
    pIp->pOrbData.l = ModPNHP(pIp->pOrbData.l, PI);
    pIp->pOrbData.delta = Asinx(su * si);
    pIp->pOrbData.cosrou = Sqrtx(Fabsx(pIp->pOrbData.r * pIp->pOrbData.r - (Re + Hco2) * (Re + Hco2)))/pIp->pOrbData.r;

    /* f.惯性系的位置和速度计算 */
    pIp->pOrbData.pos[0] = pIp->pOrbData.r * (comg * cu - somg * ci * su);
    pIp->pOrbData.pos[1] = pIp->pOrbData.r * (somg * cu + comg * ci * su);
    pIp->pOrbData.pos[2] = pIp->pOrbData.r * si * su;

    p = pIp->pOrbData.a * (1.0 - pIp->pOrbData.e * pIp->pOrbData.e);
    dr = pIp->pOrbData.e * Sinx(pIp->pOrbData.f ) * Sqrtx(Mu / p);
    h = Sqrtx(Mu * p);
    hh[0] =  h * si * somg;
    hh[1] = -h * si * comg;
    hh[2] =  h * ci;

    rdr = pIp->pOrbData.r * dr;
    rr = pIp->pOrbData.r * pIp->pOrbData.r;
    /* 星下点速度计算 */
    pIp->pOrbData.rate[0] = (pIp->pOrbData.pos[2] * hh[1] - pIp->pOrbData.pos[1] * hh[2] + pIp->pOrbData.pos[0] * rdr) / rr;
    pIp->pOrbData.rate[1] = (pIp->pOrbData.pos[0] * hh[2] - pIp->pOrbData.pos[2] * hh[0] + pIp->pOrbData.pos[1] * rdr) / rr;
    pIp->pOrbData.rate[2] = (pIp->pOrbData.pos[1] * hh[0] - pIp->pOrbData.pos[0] * hh[1] + pIp->pOrbData.pos[2] * rdr) / rr;

    return;
}