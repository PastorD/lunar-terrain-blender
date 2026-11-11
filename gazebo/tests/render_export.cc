// SDF / Gazebo Common / Ogre2 validation without network transport.
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <gz/common/Mesh.hh>
#include <gz/common/MeshManager.hh>
#include <gz/common/Image.hh>
#include <gz/rendering/RenderingIface.hh>
#include <gz/rendering/RenderEngine.hh>
#include <gz/rendering/Scene.hh>
#include <gz/rendering/Visual.hh>
#include <gz/rendering/Mesh.hh>
#include <gz/rendering/Material.hh>
#include <gz/rendering/Camera.hh>
#include <gz/rendering/Light.hh>
#include <sdf/Root.hh>
#include <sdf/World.hh>
#include <sdf/Model.hh>
#include <sdf/Link.hh>
#include <sdf/Visual.hh>
#include <sdf/Geometry.hh>
#include <sdf/Mesh.hh>
#include <sdf/Material.hh>
#include <sdf/Pbr.hh>
#include <sdf/Light.hh>
#include <sdf/Sensor.hh>
#include <sdf/Camera.hh>
#include <sdf/parser.hh>
int main(int argc,char**argv) {
 if(argc!=4){std::cerr<<"render_export WORLD PACKAGE_ROOT OUTPUT.png\n";return 2;}
 try {
  const std::string base=std::filesystem::absolute(argv[2]);
  auto resolve=[&](const std::string&s){return s.rfind("model://",0)==0?base+"/models/"+s.substr(8):s;};
  sdf::addURIPath("model://",base+"/models");sdf::Root root;auto errors=root.Load(argv[1]);
  for(auto&e:errors)std::cerr<<e<<"\n";
  if(!errors.empty()||!root.WorldCount())return 3;
  auto w=root.WorldByIndex(0);auto engine=gz::rendering::engine("ogre2",{{"headless","1"}});
  if(!engine)throw std::runtime_error("Ogre2 unavailable");
  auto scene=engine->CreateScene("lunar_offline_check");scene->SetAmbientLight(.008,.008,.008);scene->SetBackgroundColor(0,0,0);
  size_t triangles=0,count=0;
  for(uint64_t m=0;m<w->ModelCount();++m){auto model=w->ModelByIndex(m);
   for(uint64_t l=0;l<model->LinkCount();++l){auto link=model->LinkByIndex(l);
    for(uint64_t i=0;i<link->VisualCount();++i){auto v=link->VisualByIndex(i);if(!v->Geom()||!v->Geom()->MeshShape())continue;
     auto path=resolve(v->Geom()->MeshShape()->Uri());auto cm=gz::common::MeshManager::Instance()->Load(path);
     if(!cm||cm->IndexCount()%3)throw std::runtime_error("Invalid mesh: "+path);
     triangles+=cm->IndexCount()/3;++count;auto mesh=scene->CreateMesh(path);
     if(!mesh)throw std::runtime_error("Ogre mesh failed: "+path);
     auto vis=scene->CreateVisual();vis->AddGeometry(mesh);vis->SetLocalPose(model->RawPose()*link->RawPose()*v->RawPose());vis->SetLocalScale(v->Geom()->MeshShape()->Scale());
     auto mat=scene->CreateMaterial();mat->SetDiffuse(1,1,1);mat->SetAmbient(1,1,1);mat->SetSpecular(0,0,0);mat->SetRoughness(1);mat->SetMetalness(0);mat->SetCastShadows(v->CastShadows());mat->SetReceiveShadows(true);
     if(v->Material()){mat->SetDiffuse(v->Material()->Diffuse());mat->SetAmbient(v->Material()->Ambient());mat->SetEmissive(v->Material()->Emissive());}
     if(v->Material()&&v->Material()->PbrMaterial()){auto p=v->Material()->PbrMaterial()->Workflow(sdf::PbrWorkflowType::METAL);
      if(p){if(!p->AlbedoMap().empty())mat->SetTexture(resolve(p->AlbedoMap()));if(!p->NormalMap().empty())mat->SetNormalMap(resolve(p->NormalMap()));mat->SetRoughness(p->Roughness());mat->SetMetalness(p->Metalness());}}
     vis->SetMaterial(mat);scene->RootVisual()->AddChild(vis);
     std::cout<<"LOADED "<<path<<" "<<cm->IndexCount()/3<<" triangles\n"<<std::flush;
    }
   }
  }
  for(uint64_t i=0;i<w->LightCount();++i){auto s=w->LightByIndex(i);auto li=scene->CreateDirectionalLight();li->SetLocalPose(s->RawPose());li->SetDirection(s->Direction());li->SetDiffuseColor(s->Diffuse());li->SetSpecularColor(s->Specular());li->SetIntensity(s->Intensity());li->SetCastShadows(s->CastShadows());scene->RootVisual()->AddChild(li);}
  auto camera=scene->CreateCamera("lunar_camera");bool found=false;
  for(uint64_t m=0;m<w->ModelCount();++m){auto model=w->ModelByIndex(m);
   for(uint64_t l=0;l<model->LinkCount();++l){auto link=model->LinkByIndex(l);
    for(uint64_t i=0;i<link->SensorCount();++i){auto sensor=link->SensorByIndex(i);auto c=sensor->CameraSensor();if(!c)continue;
     camera->SetLocalPose(model->RawPose()*link->RawPose()*sensor->RawPose());camera->SetImageWidth(c->ImageWidth());camera->SetImageHeight(c->ImageHeight());camera->SetHFOV(c->HorizontalFov());camera->SetAspectRatio(double(c->ImageWidth())/c->ImageHeight());camera->SetNearClipPlane(c->NearClip());camera->SetFarClipPlane(c->FarClip());found=true;
    }
   }
  }
  if(!found)throw std::runtime_error("Missing SDF camera");scene->RootVisual()->AddChild(camera);camera->SetAntiAliasing(2);
  auto image=camera->CreateImage();for(int i=0;i<3;++i)camera->Capture(image);
  gz::common::Image png;png.SetFromData(image.Data<unsigned char>(),image.Width(),image.Height(),gz::common::Image::RGB_INT8);png.SavePNG(argv[3]);
  if(!std::filesystem::exists(argv[3]))throw std::runtime_error("PNG save failed");
  std::cout<<"RENDER PASS: "<<count<<" meshes, "<<triangles<<" triangles\n";
  engine->DestroyScene(scene);gz::rendering::unloadEngine("ogre2");
 }catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}
}
