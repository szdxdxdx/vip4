#include "NWM.h"
#include "CS_Track_Atti.h"

void CS_C2AngleX_temp1(void *p);
void w2dEuler_temp1(void *p);

void CS_Track_AttiFun(void *p)
{
    CS_Track_Atti *pIp = (CS_Track_Atti*)p;

    float64 tmpa[3];
    float64 tmp;

    /* [φ_Ref, θ_Ref, ψ_Ref]=DCM2Angle(Cro, Seq_AttD[WorkMode]); */
    CS_C2AngleX_temp1(pIp);
    w2dEuler_temp1(pIp);
    /* [dφ_Ref, dθ_Ref, dψ_Ref]=w2dAngle(φ_Ref, θ_Ref,ψ_Ref, ωro,
      * Seq_AttD[WorkMode]); */

    /* ddφ_Ref=(dφ_Ref-dφ_Ref_Lst)/Tc; */
    ddAtti_Ref[0] = (dAtti_Ref[0] - pIp->csMnvData_dA_Ref_Lst[0]) / Tc;

    /* ddθ_Ref=(dθ_Ref-dθ_Ref_Lst)/Tc; */
    ddAtti_Ref[1] = (dAtti_Ref[1] - pIp->csMnvData_dA_Ref_Lst[1]) / Tc;

    /* ddψ_Ref=(dψ_Ref-dψ_Ref_Lst)/Tc; */
    ddAtti_Ref[2] = (dAtti_Ref[2] - pIp->csMnvData_dA_Ref_Lst[2]) / Tc;

    /* 计算补偿力矩 */
    tmpa[0] = (wri[0] - pIp->csAttCoreData_wri_Lst[0]) / Tc;
    tmpa[1] = (wri[1] - pIp->csAttCoreData_wri_Lst[1]) / Tc;
    tmpa[2] = (wri[2] - pIp->csAttCoreData_wri_Lst[2]) / Tc;

    /* TorqRef= Js*tmpa*Mdf_TorqRef_RateTrace */
    MatrixMulti331(&TorqRef[0], &Js_All[0][0], &tmpa[0]);
    TorqRef[0] = Mdf_TorqRef * TorqRef[0];
    TorqRef[1] = Mdf_TorqRef * TorqRef[1];
    TorqRef[2] = Mdf_TorqRef * TorqRef[2];

    tmp = VectorNorm3(&TorqRef[0]);
    if (tmp > Mlf_TorqRef)
    {
        TorqRef[0] = 0.0;
        TorqRef[1] = 0.0;
        TorqRef[2] = 0.0;
    }

    Memcpyx((unint08 *)pIp->csMnvData_dA_Ref_Lst,
            (unint08 *)dAtti_Ref,
            sizeof(pIp->csMnvData_dA_Ref_Lst));
    Memcpyx((unint08 *)pIp->csAttCoreData_wri_Lst,
            (unint08 *)wri,
            sizeof(pIp->csAttCoreData_wri_Lst));

    return;
}


void CS_C2AngleX_temp1(void *p)
{
    CS_Track_Atti *pIp = (CS_Track_Atti*)p;

    switch(Seq_AttD[WorkMode])
    {
    case 123:
        C2Angle123(&Atti_Ref[0], &Cro[0][0]);
        break;
    case 132:
        C2Angle132(&Atti_Ref[0], &Cro[0][0]);
        break;
    case 213:
        C2Angle213(&Atti_Ref[0], &Cro[0][0]);
        break;
    case 231:
        C2Angle231(&Atti_Ref[0], &Cro[0][0]);
        break;
    case 312:
        C2Angle312(&Atti_Ref[0], &Cro[0][0]);
        break;
    case 321:
        C2Angle321(&Atti_Ref[0], &Cro[0][0]);
        break;
    default:
        C2Angle321(&Atti_Ref[0], &Cro[0][0]);
        break;
    }

    return;
}


void w2dEuler_temp1(void *p)
{
    CS_Track_Atti *pIp = (CS_Track_Atti*)p;
    float64 s1;
    float64 s2;
    float64 s3;
    float64 c1;
    float64 c2;
    float64 c3;

    /* 角度正弦 */
    s1 = Sinx(Atti_Ref[0]);
    s2 = Sinx(Atti_Ref[1]);
    s3 = Sinx(Atti_Ref[2]);

    /* 角度余弦 */
    c1 = Cosx(Atti_Ref[0]);
    c2 = Cosx(Atti_Ref[1]);
    c3 = Cosx(Atti_Ref[2]);

    switch (Seq_AttD[WorkMode])  /* 对转序进行判决 */
    {

    case 132:  /* 转序132 */

        dAtti_Ref[0] = (c2 * wro[0] + s2 * wro[2]) / c3;

        dAtti_Ref[1] = wro[1] + (c2 * wro[0] + s2 * wro[2]) * s3 / c3;

        dAtti_Ref[2] = - s2 * wro[0] + c2 * wro[2];

        break;

    case 321:  /* 转序321 */

        dAtti_Ref[0] = wro[0] + (s1 * wro[1] + c1 * wro[2]) * s2 / c2;

        dAtti_Ref[1] = c1 * wro[1] - s1 * wro[2];

        dAtti_Ref[2] = (s1 * wro[1] + c1 * wro[2]) / c2;

        break;

    case 312:  /* 转序312 */

        dAtti_Ref[0] = wro[0] * c2 + wro[2] * s2;

        dAtti_Ref[1] = wro[1] + (wro[0] * s2 - wro[2] * c2) * s1 / c1;

        dAtti_Ref[2] = (- wro[0] * s2 + wro[2] * c2) / c1;

        break;

    case 213:  /* 转序213 */

        dAtti_Ref[0] = c3 * wro[0] - s3 * wro[1];

        dAtti_Ref[1] = (s3 * wro[0] + c3 * wro[1]) / c1;

        dAtti_Ref[2] = wro[2] + (s3 * wro[0] + c3 * wro[1]) * s1 / c1;

        break;

    case 123:  /* 转序123 */

        dAtti_Ref[0] = (c3 * wro[0] - s3 * wro[1]) / c2 ;

        dAtti_Ref[1] = c3 * wro[1] + s3 * wro[0];

        dAtti_Ref[2] = wro[2]-(c3 * wro[0] - s3 * wro[1]) *s2/ c2;

        break;

    case 231:  /* 转序231 */

        dAtti_Ref[0] =  wro[0]-(c1 * wro[1] - s1 * wro[2]) *s3/ c3;

        dAtti_Ref[1] = (c1 * wro[1] - s1 * wro[2]) / c3;

        dAtti_Ref[2] = c1 * wro[2] + s1 * wro[1];

        break;

    default:  /* break */
        break;
    }

    return;
}