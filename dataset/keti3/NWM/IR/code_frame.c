// Point:ip_head_definition:(1)
// call:act_id:1(1):Set1
// call:act_id:2(1):Set2
// call:act_id:3(1):Set3
// call:act_id:4(1):Set4
// call:act_id:5(1):Set5
// call:act_id:6(1):Set6
// call:act_id:7(1):DetAtt1
// call:act_id:8(1):DetAtt2
// call:act_id:9(1):DetAtt3
// call:act_id:10(1):CalCtrl1
// call:act_id:11(1):CalCtrl2
// call:act_id:12(1):Set7
// call:act_id:13(1):Set8
// call:act_id:14(1):SwitchMode1
// call:act_id:15(1):Set9
// call:act_id:16(1):Set10
// call:act_id:17(1):Set11
// call:act_id:18(1):Set12
// call:act_id:19(1):CalEnv1
// call:act_id:20(1):CalEnv2
// call:act_id:21(1):CalTar1
// call:act_id:22(1):CalTar2
// call:act_id:23(1):CalTar3
// call:act_id:24(1):CalTar4
void NWMInit(void){
    // Point:ip_head_definition:(2)
    // call:act_id:1(2):Set1
// call:act_id:2(2):Set2
// call:act_id:3(2):Set3
// call:act_id:4(2):Set4
// call:act_id:5(2):Set5
// call:act_id:6(2):Set6
// call:act_id:7(2):DetAtt1
// call:act_id:8(2):DetAtt2
// call:act_id:9(2):DetAtt3
// call:act_id:10(2):CalCtrl1
// call:act_id:11(2):CalCtrl2
// call:act_id:12(2):Set7
// call:act_id:13(2):Set8
// call:act_id:14(2):SwitchMode1
// call:act_id:15(2):Set9
// call:act_id:16(2):Set10
// call:act_id:17(2):Set11
// call:act_id:18(2):Set12
// call:act_id:19(2):CalEnv1
// call:act_id:20(2):CalEnv2
// call:act_id:21(2):CalTar1
// call:act_id:22(2):CalTar2
// call:act_id:23(2):CalTar3
// call:act_id:24(2):CalTar4
    return;
}
void NWMTask(void){
    // Point:ip_head_definition:(3)
    // call:act_id:1(3):Set1
// call:act_id:2(3):Set2
// call:act_id:3(3):Set3
// call:act_id:4(3):Set4
// call:act_id:5(3):Set5
// call:act_id:6(3):Set6
if(WorkMode_Lst!= 0x00u){
                    // call:act_id:7(3):DetAtt1
// call:act_id:8(3):DetAtt2
// call:act_id:9(3):DetAtt3
// call:act_id:10(3):CalCtrl1
// call:act_id:11(3):CalCtrl2
                }
// call:act_id:12(3):Set7
// call:act_id:13(3):Set8
// call:act_id:14(3):SwitchMode1
if(WorkMode_Lst!=WorkMode){
                    // call:act_id:15(3):Set9
// call:act_id:16(3):Set10
// call:act_id:17(3):Set11
                }
if(F_DTOrbitEUpdate==1){
                    // call:act_id:18(3):Set12
                }
if(WorkMode_Lst!= 0x00u){
                    // call:act_id:19(3):CalEnv1
// call:act_id:20(3):CalEnv2
                }
if(WorkMode_Lst==0x01u){
                    // call:act_id:21(3):CalTar1
// call:act_id:22(3):CalTar2
                }
if(WorkMode_Lst==0x02u){
                    // call:act_id:23(3):CalTar3
// call:act_id:24(3):CalTar4
                }
    return;
}
# ifndef __GCC_COMPILED__
int main()
{
    NWMInit();
    while (1)
    {
        NWMTask();
    }
    return 0;
}
#endif