// Gazebo Physics / DART simulation, following gz-sim8's mesh attachment path.
#include <chrono>
#include <cmath>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <gz/plugin/Loader.hh>
#include <gz/common/Mesh.hh>
#include <gz/common/MeshManager.hh>
#include <gz/math/eigen3/Conversions.hh>
#include <gz/physics/FeatureList.hh>
#include <gz/physics/FindFeatures.hh>
#include <gz/physics/RequestEngine.hh>
#include <gz/physics/ForwardStep.hh>
#include <gz/physics/GetEntities.hh>
#include <gz/physics/FrameSemantics.hh>
#include <gz/physics/GetContacts.hh>
#include <gz/physics/mesh/MeshShape.hh>
#include <gz/physics/sdf/ConstructWorld.hh>
#include <sdf/Root.hh>
#include <sdf/World.hh>
#include <sdf/Model.hh>
#include <sdf/Link.hh>
#include <sdf/Collision.hh>
#include <sdf/Geometry.hh>
#include <sdf/Mesh.hh>
struct Features:gz::physics::FeatureList<gz::physics::sdf::ConstructSdfWorld,gz::physics::ForwardStep,gz::physics::GetModelFromWorld,gz::physics::GetLinkFromModel,gz::physics::LinkFrameSemantics,gz::physics::GetContactsFromLastStepFeature,gz::physics::mesh::AttachMeshShapeFeature>{};
int main(int argc,char**argv){
 if(argc!=4){std::cerr<<"physics_export RESOLVED_WORLD DART_PLUGIN OUTPUT.csv\n";return 2;}
 try{
  sdf::Root root;auto errors=root.Load(argv[1]);for(auto&e:errors)std::cerr<<e<<"\n";if(!errors.empty()||!root.WorldCount())return 3;auto sw=root.WorldByIndex(0);
  gz::plugin::Loader loader;loader.LoadLib(argv[2]);auto names=gz::physics::FindFeatures3d<Features>::From(loader);if(names.empty())throw std::runtime_error("DART features unavailable");
  auto plugin=loader.Instantiate(*names.begin());auto engine=gz::physics::RequestEngine3d<Features>::From(plugin);auto world=engine->ConstructWorld(*sw);if(!world)throw std::runtime_error("World construction failed");
  // ConstructSdfWorld omits mesh collisions. Gazebo Sim explicitly uses
  // Common::MeshManager + AttachMeshShape for these, as below.
  for(uint64_t m=0;m<sw->ModelCount();++m){auto model=sw->ModelByIndex(m);
   for(uint64_t l=0;l<model->LinkCount();++l){auto link=model->LinkByIndex(l);
    for(uint64_t c=0;c<link->CollisionCount();++c){auto col=link->CollisionByIndex(c);auto mesh=col->Geom()->MeshShape();if(!mesh)continue;
     auto cm=gz::common::MeshManager::Instance()->Load(mesh->Uri());
     if(!cm||cm->VertexCount()!=cm->NormalCount())throw std::runtime_error("Collision mesh lacks matching normals");
     auto pl=world->GetModel(model->Name())->GetLink(link->Name());auto shape=pl->AttachMeshShape(col->Name(),*cm,gz::math::eigen3::convert(col->RawPose()),gz::math::eigen3::convert(mesh->Scale()));
     if(!shape)throw std::runtime_error("AttachMeshShape failed");std::cout<<"ATTACHED "<<col->Name()<<" "<<cm->IndexCount()/3<<" triangles\n"<<std::flush;
    }
   }
  }
  std::ofstream csv(argv[3]);csv<<"time_s,model,x_m,y_m,z_m,vz_m_s,speed_m_s\n";
  gz::physics::ForwardStep::Input in;in.Get<std::chrono::steady_clock::duration>()=std::chrono::milliseconds(1);gz::physics::ForwardStep::State state;gz::physics::ForwardStep::Output out;bool pass=true;
  for(int step=0;step<=5000;++step){if(step)world->Step(out,state,in);if(step%100)continue;double t=step*.001;
   for(int p=0;p<6;++p){std::string name=p<5?"drop_probe_"+std::to_string(p):"freefall_probe";auto model=world->GetModel(name);if(!model)throw std::runtime_error("Missing probe");
    auto f=model->GetLink(0)->FrameDataRelativeToWorld();auto pos=f.pose.translation();csv<<t<<","<<name<<","<<pos.x()<<","<<pos.y()<<","<<pos.z()<<","<<f.linearVelocity.z()<<","<<f.linearVelocity.norm()<<"\n";
    if(p==5&&step==1000){double expected=10-.5*1.62*t*t;bool ok=std::abs(pos.z()-expected)<.002&&std::abs(f.linearVelocity.z()+1.62)<.002;pass&=ok;std::cout<<"LUNAR GRAVITY "<<(ok?"PASS":"FAIL")<<" z="<<pos.z()<<" expected="<<expected<<" vz="<<f.linearVelocity.z()<<"\n";}
    if(p<5&&step==5000){double surface=sw->ModelByName(name)->RawPose().Pos().Z()-1.1;bool ok=std::isfinite(pos.z())&&pos.z()>surface-.03&&pos.z()<surface+.8&&f.linearVelocity.norm()<.08;pass&=ok;std::cout<<"COLLISION "<<name<<" "<<(ok?"PASS":"FAIL")<<" z="<<pos.z()<<" surface="<<surface<<" speed="<<f.linearVelocity.norm()<<"\n";}
   }
  }
  auto contacts=world->GetContactsFromLastStep();pass&=!contacts.empty();std::cout<<"CONTACTS "<<contacts.size()<<"\n"<<(pass?"PHYSICS PASS":"PHYSICS FAIL")<<"\n";return pass?0:1;
 }catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}
}
